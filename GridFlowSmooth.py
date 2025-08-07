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

datelabel = str(datetime.now())[2:10] # YY-MM-DD


def beginEndLines(lines):
    '''
    takes a list of lines from psse testgrid data .RAW file.
    Returns two dictionaries with the lines beginning
    and ending each section
    '''
    ends, begins = {}, {}
    # first line is 4th line by PSSE 36, 2024
    begins["BUS"] = 2
    for i in range(len(lines)):
        line = lines[i]
        if 'END OF' in line:
            endstr, beginstr = 'END OF ', ' DATA, BEGIN '
            endof = line.find(endstr)
            begin = line.find(beginstr)
            ends[line[endof+len(endstr):begin]]= i
            begins[line[begin+len(beginstr):-6]] = i
    return begins, ends


def RAW_to_maps(filename):
    rawTx = open(filename)
    lines = rawTx.readlines()
    begins, ends = beginEndLines(lines)
    fields= {}
    fields['BUS'] = ["ibus", "name", "baskv", "ide", "area", "zone", "owner", "vm",
    "va", "nvhi", "nvlo", "evhi", "evlo"]
    fields['LOAD'] = ["ibus", "loadid", "stat", "area", "zone", "pl", "ql",
    "ip", "iq", "yp", "yq", "owner", "scale", "intrpt",
    "dgenp", "dgenq", "dgenm", "loadtype", "name"]
    fields['GENERATOR'] = ["ibus", "machid", "pg", "qg", "qt", "qb", "vs", "ireg", "nreg",
    "mbase", "zr", "zx", "rt", "xt", "gtap", "stat", "rmpct",
    "pt", "pb", "baslod", "o1", "f1", "o2", "f2", "o3", "f3", "o4",
    "f4", "wmod", "wpf","droopname","name"]
    fields['BRANCH'] = ["ibus", "jbus", "ckt", "rpu", "xpu", "bpu", "name",
    "rate1", "rate2", "rate3", "rate4", "rate5", "rate6",
    "rate7", "rate8", "rate9", "rate10", "rate11", "rate12",
    "gi", "bi", "gj", "bj", "stat", "bypass", "met", "len",
    "o1", "f1", "o2", "f2", "o3", "f3", "o4", "f4"]
    data = {}
    for cat in ['BUS', 'LOAD', 'GENERATOR', 'BRANCH']:
        data[cat] = lines[begins[cat]+1:ends[cat]]
    
    pl_idx= fields['LOAD'].index('pl')
    demands = {int(entry.split(',')[0]):float(entry.split(',')[pl_idx]) for entry in data['LOAD']}
    #we're using real power load, ignoring active
    kv_idx= fields['BUS'].index('baskv')
    basekv = {int(entry.split(',')[0]): float(entry.split(',')[kv_idx]) for entry in data['BUS']}
    pt_idx = fields['GENERATOR'].index('pt')
    gen_capacity = {int(entry.split(',')[0]): float(entry.split(',')[pt_idx]) for entry in data['GENERATOR']}
    xpu_idx = fields['BRANCH'].index('xpu')
    bpu_idx = fields['BRANCH'].index('bpu')
    rate_idx = fields['BRANCH'].index('rate1')
    x_pu= { (int(entry.split(',')[0]), int(entry.split(',')[1]), 
             int(entry.split(',')[2].replace("'",'')) ):
               float( entry.split(',')[xpu_idx]) for entry in data['BRANCH'] } 
    b_pu= { (int(entry.split(',')[0]), int(entry.split(',')[1]), 
             int(entry.split(',')[2].replace("'",'')) ):
               float( entry.split(',')[bpu_idx]) for entry in data['BRANCH'] } 
    line_capacity = { (int(entry.split(',')[0]), int(entry.split(',')[1]),
                       int(entry.split(',')[2].replace("'",'')) ):
               float( entry.split(',')[6]) for entry in data['BRANCH'] }  
    sus = { pair : -b_pu[pair]*100 for pair in x_pu}
    return {'sus': sus, 'caps':line_capacity, 
            'demands': demands, 'gen_capacity':gen_capacity}

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

def new_pairs(buses, pairs, n):
    # gets all possible pairs, picks some at random  not already in pairs
    # note that n buses can only have n*(n-1)/2 non repeating lines
    all_pairs = set(itertools.combinations(buses, 2))
    ready_pairs = set([(p[0],p[1]) for p in pairs] + [(p[1],p[0]) for p in pairs])
    remain = all_pairs - ready_pairs
    if len(remain) <= n:
        return list(remain)
    else:
        return random.sample(list(remain), n)

sus = {(1,2):200, (4,6):300, (5,7):100, (7,2):200, (1,3):200, (2,3):100, (2,4):200, (3,5):200, (1,6):200}
line_capacity = {key:sus[key]*3 for key in sus.keys()}
poss_dc_lines_cost = {(3,4):1000}
poss_dc_lines = list(poss_dc_lines_cost.keys())
poss_ac_lines_cost = {(1, 3):1e4,(2, 3):1e4, (2, 4):1e4, (3,5):1e4}
poss_ac_lines = list(poss_ac_lines_cost.keys())
dc_lines = [(3,7)]
line_capacity.update({key:1000 for key in dc_lines + poss_dc_lines})

def ACDC_TEP_OPF(gen_capacity = {1:400,2:100,5:100}, max_new_ac = 2, max_new_dc = 0, max_new = 2,
                 susceptances = sus, line_capacity = line_capacity, cut = False,
                 obj = 'cost', dc_lines = dc_lines, poss_dc_lines_cost = poss_dc_lines_cost,
                 demands = {1: 50, 2: 60, 3: 40, 4: 30, 5:50, 6:20, 7:60}, 
                 ac_lines = [(1, 2), (4,6), (5,7), (7,2)], save = False,
                 poss_ac_lines_cost = poss_ac_lines_cost,
                 printout = True, label="", generation_cost = {1: 120, 2: 25, 5: 10}):
    ## #
    ## # Saving Input # ##
    ## # 
    M = 654321
    buses = list(demands.keys())
    n = len(buses)
    gen_capacity.update({bus: 0 for bus in buses if bus not in gen_capacity.keys()})
    poss_ac_lines = list(poss_ac_lines_cost.keys())
    poss_dc_lines = list(poss_dc_lines_cost.keys())
    prob = LpProblem("Transmission_Expansion_DC_OPF", LpMinimize)    

    # Generation at each bus          ## MARK -4
    generators = gen_capacity.keys()
    gen = {b: LpVariable(f"gen_{b}", 0, gen_capacity[b]) for b in generators}
    gen.update({b: LpVariable(f"gen_{b}", 0, 0) for b in buses if b not in generators})
    
    #curtailment                       
    if cut == False:               ## MARK -3
        curtail = {b: LpVariable(f"curtail_{b}", 0, 0) for b in buses}
    else:
        curtail = {b: LpVariable(f"curtail_{b}", 0, demands[b] ) for b in buses}
               
    # Binary new lines             ## MARK -2
    new_line = {ij: LpVariable(f"new_line_{ij}", cat="Binary")
                for ij in poss_ac_lines}
    new_dc_line = {ij: LpVariable(f"new_dc_line_{ij}", cat= "Binary") 
                   for ij in poss_dc_lines}
    
    # Power flow on lines              ## MARK -1
    flow = {(ij): LpVariable(f"flow_{ij}", -line_capacity[ij], line_capacity[ij]) 
            for ij in ac_lines + poss_ac_lines}
    dc_flow = {ij: LpVariable(f"DC_flow_{ij}", -line_capacity[ij], line_capacity[ij]) 
               for ij in dc_lines + poss_dc_lines}

    # Voltage phase                    ##  MARK 0
    phase = {b: LpVariable(f"phase_{b}", -np.pi, np.pi) for b in buses}
    if obj == 'curtail':
        prob += (lpSum(curtail[b] for b in buses))  
        
        # MINIMIZE CUT POWER
    elif obj == 'cost': #              ## MARK 1
        prob += (lpSum(gen[b] * generation_cost[b] for b in generation_cost) 
                +lpSum(poss_ac_lines_cost[lin] * new_line[lin] for lin in poss_ac_lines)
                +lpSum(poss_dc_lines_cost[lin] * new_dc_line[lin] for lin in poss_dc_lines))
        # MINIMIZE COST OF FULFILLMENT
    else:
        raise ValueError(f' obj variable received {obj} rather than `cost` or `curtail`')
    # Constraints
    # 1. Power balance at each bus
    for b in buses: #                   ## MARK 2
        prob += (lpSum(flow[ij] for ij in flow if b == ij[1]) 
                 - lpSum(flow[ij] for ij in flow if b == ij[0]) 
                 + lpSum(dc_flow[ij] for ij in dc_flow if b== ij[1])
                 - lpSum(dc_flow[ij] for ij in dc_flow if b== ij[0])
                 + gen[b] + curtail[b] == demands[b], f"Power_Balance_{b}")
    
    # 2. Enforce line flow limits for candidate lines only when they are added
    for ij in poss_ac_lines: #          ## MARK 3
        prob += (flow[ij] <= line_capacity[ij]*new_line[ij] , f"Line_Capacity_Pos_{ij}")
        prob += (flow[ij] >= -line_capacity[ij]* new_line[ij] , f"Line_Capacity_Neg_{ij}")
    
    for ij in poss_dc_lines: #          ## MARK 4
        prob += (dc_flow[ij] <= line_capacity[ij]* new_dc_line[ij], f"DC_Line_Capacity_Pos_{ij}")
        prob += (dc_flow[ij] >= -line_capacity[ij] *new_dc_line[ij], f"DC_Line_Capacity_Neg_{ij}")
        
    # 3. Flow constraints based on phase differences and susceptance
    for ij in ac_lines: #              ## MARK 5
        prob += (flow[ij] == susceptances[ij] * (phase[ij[0]] - phase[ij[1]]), f"Flow_phase_{ij}")

    for ij in poss_ac_lines:           ## MARK 6
        prob += (susceptances[ij] * (phase[ij[0]] - phase[ij[1]]) - flow[ij] <= M*(1- new_line[ij]) ,     f"Line_Flow_Pos_{ij}")
        prob += (susceptances[ij] * (phase[ij[0]] - phase[ij[1]]) - flow[ij] >= -M*(1-  new_line[ij]) , f"Line_Flow_Neg_{ij}")
    
    # but DC flows freely :) as the breathed wind o'er the lush forests
    slack_gen = np.min(list(generation_cost.keys()))
    # NO REFERENCE BUS
    # prob += (phase[slack_gen] ==0 , "Reference_Bus_phase")
    #                                    ## MARK 7
    prob += (lpSum(new_line[ij] for ij in poss_ac_lines) <= max_new_ac, 'max_AC_line')
    prob += (lpSum(new_dc_line[ij] for ij in poss_dc_lines) <= max_new_dc, 'max_DC_line')
    prob += (lpSum(new_line[ij] for ij in poss_ac_lines) +
             lpSum(new_dc_line[ij] for ij in poss_dc_lines) <= max_new, 'max_lines')
    # Solve the problem
    prob.solve(pulp.GUROBI_CMD())
    
    if save:
        busM = np.zeros((n,5)) #  bus id, demand, gen_capacity, curtail, gen
        k = 0
        for i in buses:
            busM[k, 0] = i
            busM[k, 1] = demands[i]
            busM[k, 2] = gen_capacity[i]
            k+=1
        linesM = np.zeros((len(line_capacity), 9))
        k =0 
        for ij in line_capacity: # from, to, circuit, sus, cap, flow, modality, planning, 
            to = ij[0]
            fro = ij[1]
            linesM[k,:2] = np.array([fro, to])
            linesM[k,2] = 1 if len(ij)==2 else ij[2] # the circuit index, for multiple lines
            linesM[k,3] = susceptances[ij] if ij in susceptances else -1
            linesM[k,4] = line_capacity[ij]
            linesM[k,6] = 0 if ij in ac_lines + poss_ac_lines else 1 #ac = 0 or dc = 1
            linesM[k,7] = 0 if ij in ac_lines + dc_lines else 1 #fixed = 0 or suggested = 1
            k+=1
        np.save('GNN_Data/nodes'+label+'.npy', busM) #saving in case we don't converge
        np.save('GNN_Data/edges'+label+'.npy', linesM)
    ## #
    ## # SAVE OUTPUT
    ## #
    #save the output, generation, curtailment and new lines
    if pulp.LpStatus[prob.status]!='Optimal':
        if printout:
            print("Did not converge\nSee returned problem object")
            return (None, prob)
    if save:
        #  bus id, demand, gen_capacity, curtail, gen
        k = 0
        for i in buses:
            busM[k, 3] = curtail[i].varValue
            busM[k, 4] = gen[i].varValue
            k+=1
        k =0 
        for ij in susceptances: # from, to, sus, cap, flow, modality, planning, 
            to = ij[0]
            fro = ij[1]
            if ij in new_line:
                built_stat = new_line[ij].varValue
            elif ij in new_dc_line:
                built_stat = new_dc_line[ij].varValue
            else:
                built_stat = -2
            linesM[k,5] = flow[ij].varValue if ij in flow else dc_flow[ij].varValue
            linesM[k,8] =  built_stat
            k+=1
        np.save('GNN_Data/nodes'+label+'.npy', busM)
        np.save('GNN_Data/edges'+label+'.npy', linesM)
        
            
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
        for ij in ac_lines:
            # if flow[i, j].varValue >0:
            print(f"Line {ij}: {flow[ij].varValue} MW")
        if max_new_ac != 0:
            for ij in poss_ac_lines:
                print(f"New AC Line {ij}: {flow[ij].varValue} MW")
        if dc_lines != []:
            print("\nDC Line Flows:")
            for ij in dc_lines:
                print(f"Line {ij}: {dc_flow[ij].varValue} MW")
        if max_new_dc !=0:
            for ij in poss_dc_lines:
                print(f"New DC Line {ij}: {dc_flow[ij].varValue} MW")
        if max_new_dc + max_new_ac != 0:
            print("\nNew AC Line Decisions:")
            for ij in poss_ac_lines:
                print(f"Line {ij}: {'Added' if new_line[ij].varValue > 0.5 else 'Not Added'}")
            print("\nNew DC Line Decisions:")
            for ij in poss_dc_lines:
                print(f"Line {ij}: {'Added' if new_dc_line[ij].varValue > 0.5 else 'Not Added'}")
        print("\nVoltage phases:")
        for b in buses:
            print(f"Bus {b}: {phase[b].varValue} rads")
    all_out = {'gen': {i:gen[i].varValue for i in gen}, 'curtail':{i:curtail[i].varValue for i in curtail},
        'ac_lines':ac_lines, 'dc_lines':dc_lines,  
        'phase':{i:phase[i].varValue for i in phase}, 
        'possible_ac':poss_ac_lines, 'possible_dc':poss_dc_lines,
       'ac_flow':{i:flow[i].varValue for i in flow if i in ac_lines},
        'poss_ac_flow':{i:flow[i].varValue for i in flow if i in poss_ac_lines},
        'dc_flow':{i:dc_flow[i].varValue for i in dc_flow},
       'new_line':{i:new_line[i].varValue for i in new_line}, 
        'new_dc_line': {i:new_dc_line[i].varValue for i in new_dc_line} }
    return all_out, prob