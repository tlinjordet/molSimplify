# Written JP Janet
# for HJK Group
# Dpt of Chemical Engineering, MIT

##########################################################
######## Defines methods for assembling    ###############
########     RACs from lists of ligands    ###############
##########################################################
import numpy as np 
import sys

from molSimplify.Classes import mol3D
from molSimplify.Informatics.autocorrelation import*
from molSimplify.Informatics.misc_descriptors import*
from molSimplify.Informatics.graph_analyze import*

## Gets the connectivity matrix of an octahedral complex without geo
#  @param metal_mol mol3D() for the metal
#  @param custom_ligand_dict dict defining ligands (see below)
#  @return this_complex  mol3D with correct graph
def assemble_connectivity_from_parts(metal_mol, custom_ligand_dict):
    ## custom_ligand_dict.keys() must be eq_ligands_list, ax_ligand_list
    ##                                    ax_con_int_list ,eq_con_int_list
    ## with types: eq/ax_ligand2_list list of mol3D
    ##             eq/ax_con_int_list list of list/tuple of int e.g,  [[1,2] [1,2]]
    blank_mol = mol3D()
    # start with the connectivity matrix of the whole comlpex
    n_total = 1+ sum(m.mol.natoms for m in custom_ligand_dict["eq_ligand_list"]) + \
                 sum(m.mol.natoms for m in custom_ligand_dict["ax_ligand_list"])
    con_mat = np.zeros((n_total,n_total))

    this_complex = mol3D() 
    this_complex.copymol3D(metal_mol)
    live_row = 1 # metal goes in row 0 

    for i, class_lig in enumerate(custom_ligand_dict["eq_ligand_list"]):
        this_lig = class_lig.mol
        this_dim = this_lig.natoms
        this_con =  custom_ligand_dict["eq_con_int_list"][i]
        this_lig.convert2OBMol()
        this_lig.createMolecularGraph()
        con_mat[live_row:live_row + this_dim,live_row:live_row + this_dim] = this_lig.graph
        for con_atoms in this_con:
            con_mat[0,live_row + con_atoms] = 1
            con_mat[live_row + con_atoms,0] = 1
        live_row = live_row + this_dim
        this_complex.combine(this_lig,[],dirty=True)
    for i, class_lig in enumerate(custom_ligand_dict["ax_ligand_list"]):
        this_lig = class_lig.mol
        this_dim = this_lig.natoms
        this_con =  custom_ligand_dict["ax_con_int_list"][i]
        this_lig.convert2OBMol()
        this_lig.createMolecularGraph()
        con_mat[live_row:live_row + this_dim,live_row:live_row + this_dim] = this_lig.graph
        for con_atoms in this_con:
            con_mat[0,live_row + con_atoms] = 1
            con_mat[live_row + con_atoms,0] = 1
        live_row = live_row + this_dim
        this_complex.combine(this_lig,[],dirty=True)       
    if not int(sum(con_mat[:,0])) ==6:
        print('coordination number is ' + str(sum(con_mat[:,0])))
        print('error, not oct ')
        sys.exit()
    # overwrite the connectivity matrix
    this_complex.graph = con_mat
    return this_complex


## Gets the RACs of an octahedral complex without/without geo
#  @param this_complex mol3D() we want RACs for
#  @param custom_ligand_dict optional dict defining ligands (see below)
#  @return descriptor_names updated names
#  @return descriptors updated RACs
def get_descriptor_vector(this_complex,custom_ligand_dict=False,ox_modifier=False):
        descriptor_names = []
        descriptors = []
        ## misc descriptors
        results_dictionary = generate_all_ligand_misc(this_complex,loud=False,custom_ligand_dict=custom_ligand_dict)
        descriptor_names, descriptors = append_descriptors(descriptor_names, descriptors,
                                                           results_dictionary['colnames'],results_dictionary['result_ax'],'misc','ax')
        descriptor_names, descriptors = append_descriptors(descriptor_names, descriptors,
                                                           results_dictionary['colnames'],results_dictionary['result_eq'],'misc','eq')
        
        ## full ACs
        results_dictionary = generate_full_complex_autocorrelations(this_complex,depth=3,loud=False,flag_name=False)
        descriptor_names, descriptors = append_descriptors(descriptor_names, descriptors,
                                                           results_dictionary['colnames'],results_dictionary['results'],'f','all')

         ## ligand ACs
        #print('get ligand ACs')
        results_dictionary = generate_all_ligand_autocorrelations(this_complex,depth=3,loud=True,name=False,
                                                                  flag_name=False,
                                                                  custom_ligand_dict=custom_ligand_dict)
        descriptor_names, descriptors = append_descriptors(descriptor_names, descriptors,
                                                           results_dictionary['colnames'],results_dictionary['result_ax_full'],'f','ax')
        descriptor_names, descriptors =  append_descriptors(descriptor_names, descriptors,
                                                            results_dictionary['colnames'],results_dictionary['result_eq_full'],'f','eq')
        descriptor_names, descriptors =  append_descriptors(descriptor_names, descriptors,
                                                            results_dictionary['colnames'],results_dictionary['result_ax_con'],'lc','ax')
        descriptor_names, descriptors =  append_descriptors(descriptor_names, descriptors,
                                                            results_dictionary['colnames'],results_dictionary['result_eq_con'],'lc','eq')
        
        results_dictionary = generate_all_ligand_deltametrics(this_complex,depth=3,loud=False,name=False,custom_ligand_dict=custom_ligand_dict)
        descriptor_names, descriptors = append_descriptors(descriptor_names, descriptors,
                                                           results_dictionary['colnames'],results_dictionary['result_ax_con'],'D_lc','ax')
        descriptor_names, descriptors = append_descriptors(descriptor_names, descriptors,
                                                           results_dictionary['colnames'],results_dictionary['result_eq_con'],'D_lc','eq')
        
        ## metal ACs
        #print('getting metal ACs')
        results_dictionary = generate_metal_autocorrelations(this_complex,depth=3,loud=False)
        descriptor_names, descriptors =  append_descriptors(descriptor_names, descriptors,
                                                            results_dictionary['colnames'],results_dictionary['results'],'mc','all')
        results_dictionary = generate_metal_deltametrics(this_complex,depth=3,loud=False)
        descriptor_names, descriptors = append_descriptors(descriptor_names, descriptors,
                                                           results_dictionary['colnames'],results_dictionary['results'],'D_mc','all')
        ## ox-metal ACs, if ox available
        if ox_modifier:
            results_dictionary = generate_metal_ox_autocorrelations(ox_modifier, this_complex,depth=3,loud=False)
            descriptor_names, descriptors =  append_descriptors(descriptor_names, descriptors,
                                                            results_dictionary['colnames'],results_dictionary['results'],'mc','all')
            results_dictionary = generate_metal_ox_deltametrics(ox_modifier,this_complex,depth=3,loud=False)
            descriptor_names, descriptors = append_descriptors(descriptor_names, descriptors,
                                                           results_dictionary['colnames'],results_dictionary['results'],'D_mc','all')    
                                                           
        return descriptor_names, descriptors


## utility to add one-hot encoded oxidation state
## and d-electron count to some descriptors
#  @param descriptor_names RAC names, will be appended to
#  @param descriptors RAC, will be appended to
#  @param list_of_names names, will be added
#  @param list_of_props types of RACs
#  @param prefix RAC prefix
#  @param suffix RAC suffix
#  @return descriptor_names updated names
#  @return descriptors updated RACs
def create_OHE(descriptor_names,descriptors, metal,oxidation_state):
    # fucntion to append OHE encoding of oxidation state
    # and d-electron countst
    OHE_names = ['ox2','ox3','d3','d4','d5','d6','d7','d8']
    OHE_values = [   0,    0,   0,   0,   0,   0,    0, 0]
    #print(OHE_values)
    if int(oxidation_state) == 2:
        OHE_values[0]+=1
    #    print(OHE_values)
    elif int(oxidation_state) == 3:
        OHE_values[1]+=1
    if metal == "Cr" and int(oxidation_state) == 2:
        OHE_values[OHE_names.index("d4")]+=1
    elif metal == "Cr" and int(oxidation_state) == 3:
        OHE_values[OHE_names.index("d3")]+=1
    elif metal == "Mn" and int(oxidation_state) == 2:
        OHE_values[OHE_names.index("d5")]+=1
    elif metal == "Mn" and int(oxidation_state) == 3:
        OHE_values[OHE_names.index("d4")]+=1
    elif metal == "Fe" and int(oxidation_state) == 2:
        OHE_values[OHE_names.index("d6")]+=1
    elif metal == "Fe" and int(oxidation_state) == 3:
        OHE_values[OHE_names.index("d5")]+=1
    elif metal == "Co" and int(oxidation_state) == 2:
        OHE_values[OHE_names.index("d7")]+=1
    elif metal == "Co" and int(oxidation_state) == 2:
        OHE_values[OHE_names.index("d6")]+=1        
    elif metal == "Ni" and int(oxidation_state) == 2:
        OHE_values[OHE_names.index("d8")]+=1        
    else:
        print('Error: unknown metal and oxidation state '+ str(metal) +'/' +str(oxidation_state)) 
        return False

    descriptor_names = descriptor_names + OHE_names
    descriptors = descriptors +  OHE_values
        
    return descriptor_names,descriptors


## utility to build standardly formated RACS
#  @param descriptor_names RAC names, will be appended to
#  @param descriptors RAC, will be appended to
#  @param list_of_names names, will be added
#  @param list_of_props types of RACs
#  @param prefix RAC prefix
#  @param suffix RAC suffix
#  @return descriptor_names updated names
#  @return descriptors updated RACs
def append_descriptors(descriptor_names,descriptors,list_of_names,list_of_props,prefix,suffix):
    for names in list_of_names:
        if hasattr(names, '__iter__'):
            names = ["-".join([prefix,str(i),suffix]) for i in names]
            descriptor_names += names
        else:
            names = "-".join([prefix,str(names),suffix])
            descriptor_names.append(names)
    for values in list_of_props:
        if hasattr(values, '__iter__'):
            descriptors.extend(values)
        else:
            descriptors.append(values)
    return descriptor_names, descriptors
