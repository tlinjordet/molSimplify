#  @file protein3D.py
#  Defines protein3D class and contains useful manipulation/retrieval routines.
#
#  Written by HJK Group
#
#  Dpt of Chemical Engineering, MIT

# imports
from math import sqrt
import os, io
from molSimplify.Classes.AA3D import AA3D
from molSimplify.Classes.atom3D import atom3D
from molSimplify.Classes.helpers import read_atom
from molSimplify.Classes.globalvars import globalvars
import gzip
from itertools import chain
import urllib.request as urllib
import requests
from bs4 import BeautifulSoup
import pandas as pd
import string
import subprocess
import shlex
import ast
import time

# no GUI support for now

class protein3D:
    """Holds information about a protein, used to do manipulations.  Reads
    information from structure file (pdb, cif) or is directly built from
    molsimplify.
    
    """
    
    def __init__(self, pdbCode='undef'):
        # Number of amino acids
        self.naas = 0 
        # Number of atoms not part of proteins
        self.nhetatms = 0
        # Number of chains
        self.nchains = 0
        # Dictionary of amino acids
        self.aas = {}
        # Dictionary of all atoms
        self.atoms = {}
        # Dictionary of heteroatoms
        self.hetatms = {}
        # Dictionary of chains
        self.chains = {}
        # Dictionary of missing atoms
        self.missing_atoms = {}
        # List of missing amino acids
        self.missing_aas = []
        # List of possible AA conformations 
        self.conf = []
        # R value
        self.R = -1
        # Rfree value
        self.Rfree = -1
        # PDB code
        self.pdbCode = pdbCode
        # Holder for metals
        self.metals = False
        # Bonds
        self.bonds = {}
        # Data completeness
        self.DataCompleteness = 0
        # RSRZ value
        self.RSRZ = 100
        # TwinL score
        self.TwinL = 0
        # TwinL^2 score
        self.TwinL2 = 0
    
    def setAAs(self, aas):
        """ Set amino acids of a protein3D class to different amino acids.
        Parameters
        ----------
            aas : list
                Contains AA3D amino acids
        """
        self.aas = aas
        self.naas = len(aas)

    def setAtoms(self, atoms):
        """ Set atom indices of a protein3D class to atoms.
        
        Parameters
        ----------
            atoms : dictionary
                Keyed by atom index
                Valued by atom3D atom that has that index
        """
        self.atoms = atoms

    def setHetatms(self, hetatms):
        """ Set heteroatoms of a protein3D class to different heteroatoms.
        
        Parameters
        ----------
            hetatms : dictionary
                Keyed by heteroatoms
                Valued by a list containing the overarching molecule and chain
        """
        self.hetatms = hetatms
        self.nhetatms = len(hetatms.values())

    def setChains(self, chains):
        """ Set chains of a protein3D class to different chains.

        Parameters
        ----------
            chains : dictionary
                Keyed by desired chain IDs.
                Valued by the list of AA3D amino acids in the chain.
        """
        self.chains = chains
        self.nchains = len(chains.keys())

    def setMissingAtoms(self, missing_atoms):
        """ Set missing atoms of a protein3D class to a new dictionary.

        Parameters
        ----------
            missing_atoms : dictionary
                Keyed by amino acid residues of origin
                Valued by missing atoms
        """
        self.missing_atoms = missing_atoms

    def setMissingAAs(self, missing_aas):
        """ Set missing amino acids of a protein3D class to a new list.

        Parameters
        ----------
            missing_aas : list
                List of missing amino acids.
        """
        self.missing_aas = missing_aas
            
    def setConf(self, conf):
        """ Set possible conformations of a protein3D class to a new list.

        Parameters
        ----------
            conf : list
                List of possible conformations for applicable amino acids.
        """
        self.conf = conf

    def autoChooseConf(self):
        """ Automatically choose the conformation of a protein3D class
        instance based first on what the greatest occupancy level is and then
        the first conformation ihe alphabet with all else equal.

        Returns
        -------
            p : protein3D
                the same protein3D instance as self but in the automatically
                chosen conformation
        """
        p = self
        l = len(self.conf) - 1
        for i in range(l):
            if i >= len(p.conf):
                return p
            c = p.conf[i]
            c_ids = []
            for j in c.atoms:
                c_ids.append(j[0])
            a = c.atoms[0][1]
            if a.occup < 0.50 or (a.occup == 0.50 and c.loc != "A"):
                #print(c_ids)
                p.stripAtoms(c_ids)
                del p.conf[i]
        return p
            
    def setR(self, R):
        """ Set R value of protein3D class.

        Parameters
        ----------
            R : float
                The desired new R value.
        """
        self.R = R
            
    def setRfree(self, Rfree):
        """ Set Rfree value of protein3D class.

        Parameters
        ----------
            Rfree : float
                The desired new Rfree value.
        """
        self.Rfree = Rfree

    def setRSRZ(self, RSRZ):
        """ Set RSRZ score of protein3D class.

        Parameters
        ----------
            RSRZ : float
                The desired new RSRZ score.
        """
        self.RSRZ = RSRZ
            
    def getMissingAtoms(self):
        """ Get missing atoms of a protein3D class.

        """
        return self.missing_atoms.values()
    
    def getMissingAAs(self):
        """ Get missing amino acid residues of a protein3D class.

        """
        return self.missing_aas
    
    def countAAs(self):
        """ Return the number of amino acid residues in a protein3D class.

        """
        return self.naas

    def findAtom(self, sym="X"):
        """
        Find atoms with a specific symbol that are contained in amino acids.
        
        Parameters
        ----------
            sym: str
                element symbol, default as X.

        Returns
        ----------
            inds: list
                a list of atom index with the specified symbol.
        """
        inds = []
        for aa in self.aas:
            for (ii, atom) in aa.atoms:
                if atom.symbol() == sym:
                    inds.append(ii)
        return inds

    def findHetAtom(self, sym="X"):
        """
        Find heteroatoms with a specific symbol.
        
        Parameters
        ----------
            sym: str
                element symbol, default as X.

        Returns
        ----------
            inds: list
                a list of atom index with the specified symbol.
        """
        inds = []
        for (ii, atom) in self.hetatms.keys():
            if atom.symbol() == sym:
                inds.append(ii)
        return inds

    def findAA(self, three_lc="XAA"):
        """
        Find amino acids with a specific three-letter code.
        
        Parameters
        ----------
            three_lc: str
                three-letter code, default as XAA.

        Returns
        -------
            inds: set
                a set of amino acid indices with the specified symbol.
        """
        inds = set()
        for aa in self.aas:
            if aa.three_lc == three_lc:
                inds.add((aa.chain, aa.id))
        return inds

    def getChain(self, chain_id):
        """ Takes a chain of interest and turns it into its own protein3D class instance.

        Parameters
        ----------
            chain_id : string
                The letter name of the chain of interest

        Returns
        -------
            p : protein3D
                A protein3D instance consisting of just the chain of interest
        """
        p = protein3D()
        p.setChains({chain_id: self.chains[chain_id]})
        p.setAAs(set(self.chains[chain_id]))
        p.setR(self.R)
        p.setRfree(self.Rfree)
        missing_aas = []
        for aa in self.missing_aas:
            if aa.chain == chain_id:
                missing_aas.append(aa)
        p.setMissingAAs(missing_aas)
        gone_atoms = {}
        for aa in self.missing_atoms.keys():
            if aa.chain == chain_id:
                gone_atoms[aa] = self.missing_atoms[aa]
        p.setMissingAtoms(gone_atoms)
        gone_hets = self.hetatms
        atoms = {}
        for a_id in self.atoms:
            aa = self.getResidue(a_id)
            if aa != None:
                if aa.chain == chain_id:
                    atoms[a_id] = self.atoms[a_id]
            else:
                if chain_id not in gone_hets[(a_id, self.atoms[a_id])]:
                    del gone_hets[(a_id, self.atoms[a_id])]
                else:
                    atoms[a_id] = self.atoms[a_id]
        p.setHetatms(gone_hets)
        p.setAtoms(atoms)
        bonds = {}
        for a in self.bonds.keys():
            if a in p.atoms.values():
                bonds[a] = set()
                for b in self.bonds[a]:
                    if b in p.atoms.values():
                        bonds[a].add(b)
        p.setBonds(bonds)
        return p

    def getResidue(self, a_id):
        """ Finds the amino acid residue that the atom is contained in.

        Parameters
        ----------
            a_id : int
                the index of the desired atom whose residue we want to find

        Returns
        -------
            aa : AA3D
                the amino acid residue containing the atom
                returns None if there is no amino acid
        """
        for s in self.aas.values():
            for aa in s:
                if (a_id, self.atoms[a_id]) in aa.atoms:
                    return aa
        for aa in self.missing_atoms.keys():
            if (a_id, self.atoms[a_id]) in self.missing_atoms[aa]:
                return aa
        return None # the atom is a heteroatom

    def stripAtoms(self, atoms_stripped):
        """ Removes certain atoms from the protein3D class instance.
        
        Parameters
        ----------
            atoms_stripped : list
                list of atom3D indices that should be removed
        """
        atoms = self.atoms
        keys = list(self.aas.keys())
        for tup in keys:
            aminos = self.aas[tup].copy()
            for elt in aminos:
                for (a_id, atom) in elt.atoms:
                    if a_id not in self.atoms.keys():
                        continue
                    a_id = self.getIndex(atom)
                    if a_id in atoms_stripped:
                        elt.atoms.remove((a_id, atom))
                        if len(elt.atoms) == 0:
                            self.aas[tup].remove(elt)
                            if len(self.aas[tup]) == 0:
                                del self.aas[tup]
                        atoms_stripped.remove(a_id)
                        if atom in self.bonds.keys():
                            del self.bonds[atom]
                        del atoms[a_id]
        keys = list(self.hetatms.keys())
        for (h_id, hetatm) in keys:
            if (h_id, hetatm) not in self.hetatms.keys():
                continue
            if h_id in atoms_stripped:
                del self.hetatms[(h_id, hetatm)]   
                atoms_stripped.remove(h_id)
                if hetatm in self.bonds.keys():
                    del self.bonds[hetatm]
                del atoms[h_id]
        self.setAtoms(atoms)

    def stripHetMol(self, hetmol):
        """ Removes all heteroatoms part of the specified heteromolecule from
            the protein3D class instance.

        Parameters
        ----------
            hetmol : str
                String representing the name of a heteromolecule whose
                heteroatoms should be stripped from the protein3D class instance
        """
        for (h_id, hetatm) in self.hetatms.keys():
            if hetmol in self.hetatms[(h_id, hetatm)]:
                del self.hetatms[(h_id, hetatm)]
                
    def findMetal(self, transition_metals_only=True):
        """Find metal(s) in a protein3D class.
        Parameters
        ----------
            transition_metals_only : bool, optional
                Only find transition metals. Default is true.
                
        Returns
        -------
            metal_list : list
                List of indices of metal atoms in protein3D.
        """
        if not self.metals:
            metal_list = []
            for (i, atom) in self.hetatms.keys(): # no metals in AAs
                if atom.ismetal(transition_metals_only=transition_metals_only):
                    if atom.occup == 1 or atom in self.bonds.keys():
                        metal_list.append(i)
            self.metals = metal_list
        return (self.metals)

    def freezeatom(self, atomIdx):
        """Set the freeze attribute to be true for a given atom3D class.

        Parameters
        ----------
            atomIdx : int
                Index for atom to be frozen.
        """

        self.atoms[atomIdx].frozen = True

    def freezeatoms(self, Alist):
        """Set the freeze attribute to be true for a given set of atom3D classes, 
        given their indices. Preserves ordering, starts from largest index.

        Parameters
        ----------
            Alist : list
                List of indices for atom3D instances to remove.
        """

        for h in sorted(Alist, reverse=True):
            self.freezeatom(h)

    def getAtom(self, idx):
        """Get atom with a given index.

        Parameters
        ----------
            idx : int
                Index of desired atom.

        Returns
        -------
            atom : atom3D
                atom3D class for element at given index.

        """
        return self.atoms[idx]

    def getIndex(self, atom):
        """ Get index of a given atom

        Parameters
        ----------
            atom : atom3D
                atom3D class for element at given index.
            
        Returns
        -------
            idx : int
                Index of desired atom.

        """
        idx = list(self.atoms.keys())[list(self.atoms.values()).index(atom)]
        return idx
    
    def getBoundAAs(self, h_id):
        """Get a list of amino acids bound to a heteroatom, usually a metal.

        Parameters
        ----------
            h_id : int
                the index of the desired (hetero)atom origin

        Returns
        -------
            bound_aas : list
                list of AA3D instances of amino acids bound to hetatm
        """
        bound_aas = []
        aminos = globalvars().getAllAAs()
        for b_id in self.atoms.keys():
            b = self.atoms[b_id]
            if self.atoms[h_id] not in self.bonds.keys():
                return None
            elif b in self.bonds[self.atoms[h_id]] and self.getResidue(b_id) != None:
                #if self.getResidue(b_id).three_lc in aminos.keys():
                bound_aas.append(self.getResidue(b_id))
                if (b_id, b) in self.hetatms.keys():
                    # get amino acids classified as hetatms
                    b_mol = self.hetatms[(b_id, b)][0]
                    if b_mol in aminos.keys():
                        bound_aas.append(self.getResidue(b_id))
        return bound_aas
    
    def readfrompdb(self, text):
        """ Read PDB into a protein3D class instance.

        Parameters
        ----------
            text : str
                String of path to PDB file. Path may be local or global.
                May also be the text of a PDB file from the internet.
        """

        # read in PDB file
        if '.pdb' in text: # means this is a filename
            self.pdbfile = text
            fname = text.split('.pdb')[0]
            f = open(fname + '.pdb', 'r')
            text = f.read()
            enter = '\n'
            f.close()
        else:
            enter = "\\n"

        # class attributes
        aas = {}
        hetatms = {}
        atoms = {}
        chains = {}
        missing_atoms = {}
        missing_aas = []
        conf = []
        bonds = {}

        # get R and Rfree values (text is full file)
        if "R VALUE            (WORKING SET)" in text:
            temp = text.split("R VALUE            (WORKING SET)")
            temp2 = temp[-1].split()
            if temp2[1] != 'NULL':
                R = float(temp2[1])
            else:
                R = -100
            if temp2[8] != 'NULL':
                Rfree = float(temp2[8])
            else:
                Rfree = 100
        else:
            temp = text.split("R VALUE          (WORKING SET, NO CUTOFF)")
            temp2 = temp[-1].split()
            if temp2[1] != 'NULL':
                R = float(temp2[1])
            else:
                R = -100
            if temp2[10] != 'NULL':
                Rfree = float(temp2[10])
            else:
                Rfree = 100
        temp = temp[1].split(enter)

        # start getting missing amino acids
        if "M RES C SSSEQI" in text:
            text = text.split("M RES C SSSEQI")
            want = text[-1]
            text = text[0].split(enter)
            split = text[-1]
            want = want.split(split)
            for line in want:
                if line == want[-1]:
                    text = line
                    line = line.split(enter)
                    line = line[0]
                    text = text.replace(line, '')
                l = line.split()
                if len(l) > 2:
                    a = AA3D(l[0], l[1], l[2])
                    missing_aas.append(a)

        # start getting missing atoms
        if "M RES CSSEQI  ATOMS" in text:
            text = text.split("M RES CSSEQI  ATOMS")
            want = text[-1]
            text = text[0].split(enter)
            split = text[-1]
            want = want.split(split)
            for line in want:
                if line == want[-1]: 
                    text = line
                    line = line.split(enter)
                    line = line[0]
                    text = text.replace(line, '')
                l = line.split()
                if len(l) > 2:
                    missing_atoms[(l[1],l[2])] = []
                    for atom in l[3:]:
                        if atom != enter and atom[0] in ['C', 'N', 'O', 'H']:
                            missing_atoms[(l[1],l[2])].append(atom3D(Sym=atom[0],
                                                           greek=atom))
        # start getting amino acids and heteroatoms
        prev_a_dict = {'AltLoc': ""}
        if "ENDMDL" in text:
            text.split("ENDMDL")
            text = text[-2] + text[-1]
        text = text.split(enter)
        text = text[1:]
        for line in text:
            if line == text[-1]:
                text = line
                line = line.split(enter)
                line = line[0]
                text = text.replace(line, '')
            l_type = line[:6]
            if "ATOM" in l_type: # we are in an amino acid
                line = line.replace("\\'", "\'")
                a_dict = read_atom(line)
                a, aas, conf, prev_a_dict = make_aa(a_dict, aas, prev_a_dict)
                atom = atom3D(Sym=a_dict['Element'], xyz=[a_dict['X'],
                                                          a_dict['Y'],
                                                          a_dict['Z']],
                              Tfactor=a_dict['TempFactor'],
                              occup=a_dict['Occupancy'], greek=a_dict['Name'])
                a.addAtom(atom, a_dict['SerialNum']) # terminal Os may be missing
                atoms[a_dict['SerialNum']] = atom
                a.setBonds()
                bonds.update(a.bonds)
                if a.prev != None:
                    bonds[a.n].add(a.prev.c)
                if a.next != None:
                    bonds[a.c].add(a.next.n)

            elif "HETATM" in l_type: # this is a heteroatom
                line = line.replace("\\'", "\'")
                a_dict = read_atom(line)
                aminos = globalvars().getAllAAs()
                fake_aa = False
                loc = a_dict['AltLoc']
                if a_dict['ResName'] in aminos:
                    fake_aa = True # an AA is masquerading as hetatms :P
                    a, aas, conf, prev_a_dict = make_aa(a_dict, aas, prev_a_dict)
                hetatm = atom3D(Sym=a_dict['Element'], xyz = [a_dict['X'],
                                                              a_dict['Y'],
                                                              a_dict['Z']],
                                Tfactor=a_dict['TempFactor'],
                                occup=a_dict['Occupancy'], greek=a_dict['Name'])
                if fake_aa:
                    a.addAtom(hetatm, a_dict['SerialNum']) # terminal Os may be missing
                    a.setBonds()
                    bonds.update(a.bonds)
                    if a.prev != None:
                        bonds[a.n].add(a.prev.c)
                    if a.next != None:
                        bonds[a.c].add(a.next.n)
                elif (a_dict['SerialNum'], hetatm) not in hetatms.keys():
                    
                    hetatms[(a_dict['SerialNum'], hetatm)] = [a_dict['ResName'], a_dict['ChainID']]
                atoms[a_dict['SerialNum']] = hetatm

            elif "CONECT" in l_type: # get extra connections
                line = line[6:] # remove type
                l = [line[i:i+5] for i in range(0, len(line), 5)]
                if int(l[0]) in atoms.keys() and atoms[int(l[0])] not in bonds.keys():
                    bonds[atoms[int(l[0])]] = set()
                for i in l[1:]:
                    try:
                        bonds[atoms[int(l[0])]].add(atoms[int(i)])
                    except:
                        if "  " not in i and i != " ":
                            print("likely OXT")
                        continue
        # deal with conformations in chains
        for i in range(len(conf)-1):
            if conf[i].chain == conf[i+1].chain and conf[i].id == conf[i+1].id:
                if conf[i].occup >= conf[i+1].occup:
                    chains[conf[i].chain].append(conf[i])
                    # pick chain with higher occupancy or the A chain if tie
                else:
                    chains[conf[i+1].chain].append(conf[i+1])
        self.setChains(chains)
        self.setAAs(aas)
        self.setAtoms(atoms)
        self.setHetatms(hetatms)
        self.setMissingAtoms(missing_atoms)
        self.setMissingAAs(missing_aas)
        self.setConf(conf)
        self.setR(R)
        self.setRfree(Rfree)
        self.setBonds(bonds)

    def fetch_pdb(self, pdbCode):
        """ API query to fetch a pdb and write it as a protein3D class instance

        Parameters
        ----------
            pdbCode : str
                code for protein, e.g. 1os7
        """
        remoteCode = pdbCode.upper()
        try:
            data = urllib.urlopen(
                'https://files.rcsb.org/view/' + remoteCode +
                '.pdb').read()
        except:
            print("warning: %s not found.\n"%pdbCode)
        else:
            try:
                self.readfrompdb(str(data))
                self.setPDBCode(pdbCode)
                print("fetched: %s"%(pdbCode))
            except IOError:
                print('aborted')
            else:
                if len(data) == 0:
                    print("warning: %s not valid.\n"%pdbCode)

    def setBonds(self, bonds):
        """Sets the bonded atoms in the protein.
        This is effectively the molecular graph.
         
        Parameters
        ----------
            bonds : dictionary
                Keyed by atom3D atoms in the protein
                Valued by a set consisting of bonded atoms
        """
        self.bonds = bonds

    def readMetaData(self):
        """ API query to fetch XML data from a pdb and add its useful attributes
        to a protein3D class.
        
        Parameters
        ----------
            pdbCode : str
                code for protein, e.g. 1os7
        """
        pdbCode = self.pdbCode
        try:
            start = 'https://files.rcsb.org/pub/pdb/validation_reports/' + pdbCode[1] + pdbCode[2]
            link = start + '/' + pdbCode + '/' + pdbCode + '_validation.xml'
            xml_doc = requests.get(link)
        except:
            print("warning: %s not found.\n"%pdbCode)
        else:
            try:
                ### We then use beautiful soup to read the XML doc. LXML is an XML reader. The soup object is what we then use to parse!
                soup = BeautifulSoup(xml_doc.content,'lxml-xml')
                
                ### We can then use methods of the soup object to find "tags" within the XML file. This is how we would extract sections. 
                ### This is an example of getting everything with a "sec" tag.
                body = soup.find_all('wwPDB-validation-information')
                entry = body[0].find_all("Entry")
                #print("got metadata: %s"%(pdbCode))
                if "DataCompleteness" not in entry[0].attrs.keys():
                    self.setDataCompleteness(0)
                    print("warning: %s has no DataCompleteness."%pdbCode)
                else:
                    self.setDataCompleteness(float(entry[0].attrs["DataCompleteness"]))
                if "percent-RSRZ-outliers" not in entry[0].attrs.keys():
                    self.setRSRZ(100)
                    print("warning: %s has no RSRZ.\n"%pdbCode)
                else:
                    self.setRSRZ(float(entry[0].attrs["percent-RSRZ-outliers"]))
                if "TwinL" not in entry[0].attrs.keys():
                    print("warning: %s has no TwinL."%pdbCode)
                    self.setTwinL(0)
                else:
                    self.setTwinL(float(entry[0].attrs["TwinL"]))
                if "TwinL2" not in entry[0].attrs.keys():
                    print("warning: %s has no TwinL2."%pdbCode)
                    self.setTwinL2(0)
                else:
                    self.setTwinL2(float(entry[0].attrs["TwinL2"]))
            except IOError:
                print('aborted')
            else:
                if xml_doc == None:
                    print("warning: %s not valid.\n"%pdbCode)

    def setDataCompleteness(self, DataCompleteness):
        """ Set DataCompleteness value of protein3D class.

        Parameters
        ----------
            DataCompleteness : float
                The desired new R value.
        """
        self.DataCompleteness = DataCompleteness

    def setTwinL(self, TwinL):
        """ Set TwinL score of protein3D class.

        Parameters
        ----------
            TwinL : float
                The desired new TwinL score.
        """
        self.TwinL = TwinL

    def setTwinL2(self, TwinL2):
        """ Set TwinL squared score of protein3D class.

        Parameters
        ----------
            TwinL2 : float
                The desired new TwinL squared score.
        """
        self.TwinL2 = TwinL2

    def setEDIAScores(self):
        """ Sets the EDIA score of a protein3D class.

        Parameters
        ----------
            pdbCode : string
                The 4-character code of the protein3D class.
        """
        code = self.pdbCode
        cmd = 'curl -d \'{"edia":{ "pdbCode":"'+code+'"}}\' -H "Accept: application/json" -H "Content-Type: application/json" -X POST https://proteins.plus/api/edia_rest'
        args = shlex.split(cmd)
        result = subprocess.Popen(args, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        result.wait()
        out, err = result.communicate()
        dict_str = out.decode("UTF-8")
        int_dict = ast.literal_eval(dict_str)
        res2 = subprocess.Popen(['curl', int_dict['location']],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out2, err2 = res2.communicate()
        dict2_str = out2.decode("UTF-8")
        dictionary = ast.literal_eval(dict2_str)
        t = 20
        while dictionary["status_code"] == 202:
            res2 = subprocess.Popen(['curl', int_dict['location']],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            print('sleeping', t)
            time.sleep(t)
            res2.wait()
            out2, err2 = res2.communicate()
            dict2_str = out2.decode("UTF-8")
            dictionary = ast.literal_eval(dict2_str)
            t += 5
        link = dictionary["atom_scores"]
        df = pd.read_csv(link, error_bad_lines=False)
        for i, row in df.iterrows():
            EDIA = row["EDIA"]
            index = row["Infile id"]
            if index in self.atoms.keys():
                a = self.atoms[index]
                a.setEDIA(EDIA)
                if a.occup < 1: # more than one conformation
                    subdf = df[df["Infile id"]==index+1]
                    if subdf.shape[0] == 0 and index+1 in self.atoms.keys():
                        self.atoms[index+1].setEDIA(EDIA)
                    elif subdf.shape[0] == 0 and index-1 in self.atoms.keys():
                        self.atoms[index-1].setEDIA(EDIA)
            else:
                print("OXT is missing")

    def setPDBCode(self, pdbCode):
        """ Sets the 4-letter PDB code of a protein3D class instance

        Parameters
        ----------
            pdbCode : string
                Desired 4-letter PDB code
        """
        self.pdbCode = pdbCode

