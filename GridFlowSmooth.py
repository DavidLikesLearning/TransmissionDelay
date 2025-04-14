from datetime import datetime
import numpy as np
import pandas as pd
import copy
import pulp
import matplotlib.pyplot as plt
import time
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpBinary, value
import pulp
import csv
import random

#UPDATED 11 APRIL 2025. ACDC TEP AGREES WITH PANDAPOWER

datelabel = str(datetime.now())[2:10]

def first_bus(line):
    #along with is_first_bus(), determines beginning of bus data in raw file
    #does so by counting the different numbers present
    #as introductory lines have less numbers
    chopped = line.replace(' ','').replace('.','').replace('\n', '').replace('-','').split(',')
    decimal_bin = [i.isdecimal() for i in chopped]
    return np.sum(decimal_bin), len(decimal_bin)

def is_first_bus(line):
    #see first_bus_line()
    nums, pieces = first_bus(line)
    if nums>=8 and pieces-nums <=2:
        return True
    return False

def get_sects(lines):
    #get line indeces for the various sections of a grid data RAW file
    #will handle begining of bus section separately
    begin_ends = {}
    found_bus = False
    j = 0
    while not found_bus:
        if is_first_bus(lines[j]):
            begin_ends['BUS'] = np.array([j-1,0])
            found_bus = True
        j+=1
    #bus section handled, every other section nicely marked with 'BEGIN' and 'END OF'
    k = 0
    for i in range(len(lines)):
        if 'BEGIN ' in lines[i]:
            a = lines[i].find('BEGIN ')
            b = lines[i].find(' DATA',a)
            datatype = lines[i][a+len('BEGIN '):b]
            begin_ends[datatype] = np.array([i,0])
        if 'END OF ' in lines[i]:
            a = lines[i].find('END OF ')
            b = lines[i].find(' DATA')
            datatype = lines[i][a+len('END OF '):b]
            if datatype in begin_ends:
                begin_ends[datatype] += np.array([0,i])
            else:
                begin_ends[datatype] = np.array([0,i])
                
    return begin_ends     

def which_sect(i,begin_ends):
    #given the line index and the bounds on sections
    #we know we are in the X section if we're in the bounds
    for key in begin_ends.keys():
        lo, hi = tuple(begin_ends[key])
        if i >lo and i< hi:
            return key
    return 'OOPS'

def read_RAW(lines):
    #processes RAW file containing grid data
    #generates lists of dictionaries for each
    #bus, generator, branch, load
    begin_ends = get_sects(lines)
    Buses, Generators, Branches, Loads = [], [], [], []
    i = 0
    while i<len(lines):
        line = lines[i]
        sec = which_sect(i,begin_ends)
        if sec =='BUS':
            ew_data = line.split(',')
            data = []
            for k in ew_data:
                data.append(k.strip(" '"))
            Buses.append({
                'bus_id': int(data[0]),
                'voltage_mag': float(data[7]),
                'voltage_angle': float(data[8]),
                'type': float(data[3]),   
                'base_kv': float(data[2])  })
        elif sec == 'GENERATOR':
                    # Generator data: [Bus ID, Generation P, Generation Q, Max P, Min P]
                    ew_data = line.split(',')
                    data = []
                    for k in ew_data:
                        data.append(k.strip(" '"))
                    Generators.append({
                        'bus_id': int(data[0]),
                        'gen_p': float(data[2]),
                        'gen_q': float(data[3]),
                        'max_p': float(data[4]),
                        'min_p': float(data[5]),
                        'mbase': float(data[8])  })
        elif sec == 'BRANCH':
                    # Branch data: [From Bus, To Bus, Resistance, Reactance, Line Charging]
                    ew_data = line.split(',')
                    data = []
                    for k in ew_data:
                        data.append(k.strip(" '"))
                    Branches.append({
                        'from_bus': int(data[0]),
                        'to_bus': int(data[1]),
                        'resistance': float(data[3]),
                        'reactance': float(data[4]),
                        'line_charging': float(data[5])  })
        elif sec == 'LOAD':
                    # Branch data: [From Bus, To Bus, Resistance, Reactance, Line Charging]
                    ew_data = line.split(',')
                    data = []
                    for k in ew_data:
                        data.append(k.strip(" '"))
                    Loads.append({
                        'bus_id': int(data[0]),
                        'status': int(data[2]),
                        'PL': float(data[5]),
                        'QL': float(data[6]),
                        'LOAD_MAG': np.round(np.sqrt(float(data[5])**2 + float(data[6])**2), 2),
                        'IP': float(data[7]),
                        'IQ': float(data[8]) })
        i+=1
    return (Buses, Generators, Branches, Loads)

def branch2pairs(Branches):
    pairs = []                     
    for key in Branches:
        pairs.append((key['to_bus'],key['from_bus']))
    return pairs

def get_sus(x,r):
    #susceptance from resistance, reactance
    return -1/x

def suggest_lines(pairs, bus_list, n=3):
    # generates `n` recommended new pairs from the existing pairs and the list of buses
    # essentially cuts bus lists into `n` sections and searches for non existing lines
    out = []
    for i in range(n):
        start = (len(bus_list)//n)*i
        shift = 1
        while len(out)<i+1:
            new_pair = (bus_list[start], bus_list[start+shift])
            if new_pair not in pairs+out and (new_pair[1],new_pair[0]) not in pairs+out:
                out.append(new_pair)
            shift+=1
    return out

def ACDC_TEP_OPF(gen_capacity = {1:100,2:100,3:0,4:0,5:100, 6:0, 7:0}, line_capacity = 1000, 
                 susceptances = {(1,2):.1, (4,6):.1, (5,7):.1, (7,2):.1, (1,3):.1, (2,3):.1, (2,4):.1, (3,5):.1}, 
                 line_expansion_cost = 1000, buses = [1, 2, 3, 4, 5, 6, 7], obj = 'curtail',
                 demands = {1: 50, 2: 60, 3: 40, 4: 30, 5:50, 6:20, 7:60}, cut = False,
                 ac_lines = [(1, 2), (4,6), (5,7), (7,2)], poss_ac_lines = [(1, 3),(2, 3), (2, 4), (3,5)],
                 dc_lines = [(3,4)], poss_dc_lines = [(3,4)], generation_cost = {1: 120, 2: 25, 5: 10},
                 printout = False, max_new_ac = 1, max_new_dc = 0, label=datelabel, save = True):
    #saving input
    M = 54321
    n = len(buses)
    if save:
        busM = np.zeros((n,3)) #  bus id, demand, gen_capacity
        k = 0
        for i in buses:
            busM[k, 0] = i
            busM[k, 1] = demands[i]
            busM[k, 2] = gen_capacity[i]
            k+=1
        # saving node_from, node_to, sus, capacity to later rebuild adjacency matrix 
        # AC, new AC, old DC, then new DC. separated by rows of -1s

        old_ac = np.array([(ac[0], ac[1], susceptances[ac], line_capacity) for ac in ac_lines])
        new_ac = np.array([(ac[0], ac[1], susceptances[ac], line_capacity) for ac in poss_ac_lines])
        old_dc = np.array([(dc[0], dc[1],0, line_capacity) for dc in dc_lines])
        new_dc = np.array([(dc[0], dc[1],0, line_capacity) for dc in poss_dc_lines])
        pause =- np.array([[1,1,1,1]])
        if dc_lines == []: # concatinating the empty array of dc lines is an issue
            connections = np.concatenate([old_ac, pause, new_ac, pause, new_dc], axis=0)
        else:
            connections = np.concatenate([old_ac, pause, new_ac, pause, old_dc, pause, new_dc], axis=0)
            
        np.save('GNN_Data/busM'+label+'.npy', busM)
        np.save('GNN_Data/linesM'+label+'.npy', connections )
 
    prob = LpProblem("Transmission_Expansion_DC_OPF", LpMinimize)    
    # Decision Variables
    # Generation at each bus
    generators = gen_capacity.keys()
    gen = {b: LpVariable(f"gen_{b}", 0, gen_capacity[b]) for b in generators}
    gen.update({b: LpVariable(f"gen_{b}", 0, 0) for b in buses if b not in generators})
    
    #curtailment
    if cut == False:
        curtail = {b: LpVariable(f"curtail_{b}", 0, 0) for b in buses}
    else:
        curtail = {b: LpVariable(f"curtail_{b}", 0, demand[b] ) for b in buses}
               
    # Binary variables for new lines
    new_line = {(i, j): LpVariable(f"new_line_{i}_{j}", cat="Binary")
                for i, j in poss_ac_lines}
    new_dc_line = {(i,j): LpVariable(f"new_dc_line_{i}_{j}", cat= "Binary") 
                   for i, j in poss_dc_lines}
    
    # Power flow on lines
    flow = {(i, j): LpVariable(f"flow_{i}_{j}", -line_capacity, line_capacity) 
            for i, j in ac_lines + poss_ac_lines}
    dc_flow = {(i,j): LpVariable(f"DC_flow_{i}_{j}", -line_capacity, line_capacity) 
               for i, j in dc_lines + poss_dc_lines}

    # Voltage phase at each bus (reference phase at bus 1 is 0)
    phase = {b: LpVariable(f"phase_{b}", -np.pi/6, np.pi/6) for b in buses}
    if obj == 'curtail':
        prob += (lpSum(curtail[b] for b in buses)) 
        
        # MINIMIZE CUT POWER
    elif obj == 'cost':
        prob += (lpSum(gen[b] * generation_cost[b] for b in generation_cost) )
        # MINIMIZE COST OF FULFILLMENT
    else:
        raise ValueError(f' obj variable received {obj} rather than `cost` or `curtail`')
    # Constraints
    # 1. Power balance at each bus
    for b in buses:
        prob += (lpSum(flow[i, b] for i, _ in flow if b == _) 
                 - lpSum(flow[b, j] for _, j in flow if b == _) 
                 + lpSum(dc_flow[i, b] for i, _ in dc_flow if b== _)
                 - lpSum(dc_flow[b, j] for _, j in dc_flow if b== _)
                 + gen[b] + curtail[b] == demands[b], f"Power_Balance_{b}")
    
    # 2. Enforce line flow limits for candidate lines only when they are added
    for i, j in poss_ac_lines:
        prob += (flow[i, j] <= line_capacity*new_line[i, j] , f"Line_Capacity_Pos_{i}_{j}")
        prob += (flow[i, j] >= -line_capacity* new_line[i, j] , f"Line_Capacity_Neg_{i}_{j}")
    

    for i, j in poss_dc_lines:
        prob += (dc_flow[i, j] <= line_capacity* new_dc_line[i, j], f"DC_Line_Capacity_Pos_{i}_{j}")
        prob += (dc_flow[i, j] >= -line_capacity *new_dc_line[i, j], f"DC_Line_Capacity_Neg_{i}_{j}")
        
    # 3. Flow constraints based on phase differences and susceptance
    for i, j in ac_lines: #+ poss_ac_lines:
        prob += (flow[i, j] == susceptances[(i,j)] * (phase[i] - phase[j]), f"Flow_phase_{i}_{j}")

    for i, j in poss_ac_lines:
        prob += (susceptances[(i,j)] * (phase[i] - phase[j]) - flow[i, j] <= M*(1- new_line[i, j]) , f"Line_Flow_Pos_{i}_{j}")
        prob += (susceptances[(i,j)] * (phase[i] - phase[j]) - flow[i, j] >= -M*(1-  new_line[i, j]) , f"Line_Flow_Neg_{i}_{j}")
    
    
    # but DC flows freely :) as the breathed wind o'er the lush forests
    slack_gen = np.min(list(generation_cost.keys()))
    # 4. Set reference bus phase to 0
    prob += (phase[slack_gen] ==0 , "Reference_Bus_phase")
    prob += (lpSum(new_line[(i,j)] for i,j in poss_ac_lines) <= max_new_ac, 'max_AC_line')
    prob += (lpSum(new_dc_line[(i,j)] for i,j in poss_dc_lines) <= max_new_dc, 'max_DC_line')
    # Solve the problem
    prob.solve()


    #save the output, generation, curtailment and new lines
    if save:
        busY = np.zeros((n,3)) #  buses' curtailment, generation
        k = 0
        for i in buses:
            busY[k,0] = i
            busY[k,1] = curtail[i].varValue
            busY[k,2] = gen[i].varValue
            k+=1
        #output records matrix for new AC, then new DC
        #each row has from_node, to_node, susceptance, capacity, added. 
        #separated by rows of -1s
        added_ac = [(i,j, susceptances[i,j], line_capacity, new_line[i,j].varValue) for (i,j) in new_line]
        added_dc = [(i,j, 0, line_capacity, new_dc_line[i,j].varValue) for (i,j) in new_dc_line]
        pause =- np.array([[1,1,1,1,1]])
        new_connections = np.concatenate([added_ac, pause, added_dc], axis=0)
        
        np.save('GNN_Data/busY'+label+'.npy', busY)
        np.save('GNN_Data/linesNewY'+label+'.npy', new_connections)
    
    # Print results
    if printout:
        print("Status:", pulp.LpStatus[prob.status])
        print("Objective Value:", value(prob.objective))
        print("\nGeneration at Each Bus:")
        for b in buses:
            if gen[b].varValue>0:
                print(f"Bus {b}: {gen[b].varValue} MW")
        if cut == True:
            print("\nCurtailment:")
            for b in buses:
                if curtail[b].varValue>0:
                    print(f"Bus {b}: {curtail[b].varValue} MW")
        print("\nAC Line Flows:")
        for i, j in ac_lines + poss_ac_lines:
            # if flow[i, j].varValue >0:
            print(f"Line {i}-{j}: {flow[i, j].varValue} MW")
        if dc_lines != []:
            print("\nDC Line Flows:")
            for i, j in dc_lines + poss_dc_lines:
                print(f"Line {i}-{j}: {dc_flow[i, j].varValue} MW")
        if max_new_dc + max_new_ac != 0:
            print("\nNew AC Line Decisions:")
            for i, j in poss_ac_lines:
                print(f"Line {i}-{j}: {'Added' if new_line[i, j].varValue > 0.5 else 'Not Added'}")
            print("\nNew DC Line Decisions:")
            for i, j in poss_dc_lines:
                print(f"Line {i}-{j}: {'Added' if new_dc_line[i, j].varValue > 0.5 else 'Not Added'}")
        print("\nVoltage phases:")
        for b in buses:
            print(f"Bus {b}: {phase[b].varValue} rads")
    all_out = {'gen': {i:gen[i].varValue for i in gen}, 'curtail':{i:curtail[i].varValue for i in curtail},
        'ac_lines':ac_lines, 'dc_lines':dc_lines,  'phase':{i:phase[i].varValue for i in phase}, 
        'possible_ac':poss_ac_lines, 'possible_dc':poss_dc_lines,
       'ac_flow':{i:flow[i].varValue for i in flow}, 'dc_flow':{i:dc_flow[i].varValue for i in dc_flow},
       'new_line':{i:new_line[i].varValue for i in new_line}, 
        'new_dc_line': {i:new_dc_line[i].varValue for i in new_dc_line} }
    return all_out, prob
