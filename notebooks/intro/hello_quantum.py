#!/usr/bin/env python3

import copy
from io import BytesIO

from qiskit import BasicAer as Aer
from qiskit import ClassicalRegister, QuantumRegister, QuantumCircuit
from qiskit import execute
from qiskit.visualization import plot_bloch_multivector
from qiskit.quantum_info import Statevector

from qiskit.quantum_info import Statevector
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
from ipywidgets import widgets
from IPython.display import display

from qiskit_textbook.widgets._helpers import _img

darker_purple = (105/255, 41/255, 196/255)
dark_purple = 165/255, 110/255, 1
purple = 190/255, 149/255, 1
light_purple = 212/255, 187/255, 1

white = (242/255,244/255,248/255)
light_gray = (221/255,225/255,230/255)
dark_gray = (193/255,199/255,205/255)
black = (52/255,58/255,63/255)


# background color
background_color = white
# circle colors for normal and Y circles
circle_color = [white,white]
# colors for 0 and 1 parts of line and divider
line_color = [light_gray,purple,dark_purple]
# box colors for qubit boxes and correlation boxes
box_color = [light_purple,darker_purple]
# outer and inner colors of Bloch point
point_color = [dark_gray,dark_gray]


class run_game():
    # Implements a puzzle, which is defined by the given inputs.

    def __init__(self,initialize, success_condition, allowed_gates, vi, qubit_names={'0':'q[0]', '1':'q[1]'}, eps=0.1, backend=None, shots=1024,mode='line',verbose=False):
        """
        initialize
            List of gates applied to the initial 00 state to get the starting state of the puzzle.
            Supported single qubit gates (applied to qubit '0' or '1') are 'x', 'y', 'z', 'h', 'ry(pi/4)'.
            Supported two qubit gates are 'cz' and 'cx'. Specify only the target qubit.
        success_condition
            Values for pauli observables that must be obtained for the puzzle to declare success.
        allowed_gates
            For each qubit, specify which operations are allowed in this puzzle. 'both' should be used only for operations that don't need a qubit to be specified ('cz' and 'unbloch').
            Gates are expressed as a dict with an int as value. If this is non-zero, it specifies the number of times the gate is must be used (no more or less) for the puzzle to be successfully solved. If the value is zero, the player can use the gate any number of times.
        vi
            Some visualization information as a three element list. These specify:
            * which qubits are hidden (empty list if both shown).
            * whether both circles shown for each qubit (use True for qubit puzzles and False for bit puzzles).
            * whether the correlation circles (the four in the middle) are shown.
        qubit_names
            The two qubits are always called '0' and '1' from the programming side. But for the player, we can display different names.
        eps=0.1
            How close the expectation values need to be to the targets for success to be declared.
        backend=Aer.get_backend('qasm_simulator')
            Backend to be used by Qiskit to calculate expectation values (defaults to local simulator).
        shots=1024
            Number of shots used to to calculate expectation values.
        mode='circle'
            Either the standard 'Hello Quantum' visualization can be used (with mode='circle'), or the extended one (mode='y') or the alternative line based one (mode='line').
        y_boxes = False
            Whether to show expectation values involving y.
        verbose=False
        """

        def get_total_gate_list():
            # Get a text block describing allowed gates.

            total_gate_list = ""
            for qubit in allowed_gates:
                gate_list = ""
                for gate in allowed_gates[qubit]:
                    if required_gates[qubit][gate] > 0:
                        gate_list += (
                            f'  {gate} (use {str(required_gates[qubit][gate])} time'
                            + "s" * (required_gates[qubit][gate] > 1)
                            + ")"
                        )
                    elif allowed_gates[qubit][gate]==0:
                        gate_list += f'  {gate} '
                if gate_list!="":
                    if qubit=="both" :
                        gate_list = "\nAllowed symmetric operations:" + gate_list
                    else :
                        gate_list = "\nAllowed operations for " + qubit_names[qubit] + ":\n" + " "*10 + gate_list
                    total_gate_list += gate_list +"\n"
            return total_gate_list

        def get_success(required_gates):
            # Determine whether the success conditions are satisfied, both for expectation values, and the number of gates to be used.

            success = True
            grid.get_rho()
            if verbose:
                print(grid.rho)
            for pauli in success_condition:
                success = success and (abs(success_condition[pauli] - grid.rho[pauli])<eps)
            for qubit in required_gates:
                for gate in required_gates[qubit]:
                    success = success and (required_gates[qubit][gate]==0)
            return success

        def show_circuit():
            gates = get_total_gate_list

        def get_command(gate,qubit):
            # For a given gate and qubit, return the string describing the corresponding Qiskit string.

            if qubit=='both':
                qubit = '1'
            qubit_name = qubit_names[qubit]
            for name in qubit_names.values():
                if name!=qubit_name:
                    other_name = name
            # then make the command (both for the grid, and for printing to screen)
            if gate in ['x','y','z','h']:
                real_command = f'grid.qc.{gate}(grid.qr[{qubit}])'
                clean_command = f'qc.{gate}({qubit_name})'
            elif gate in ['ry(pi/4)','ry(-pi/4)']:
                real_command  = 'grid.qc.ry('+'-'*(gate=='ry(-pi/4)')+'np.pi/4,grid.qr['+qubit+'])'
                clean_command = 'qc.ry('+'-'*(gate=='ry(-pi/4)')+'np.pi/4,'+qubit_name+')'
            elif gate in ['rx(pi/4)','rx(-pi/4)']:
                real_command  = 'grid.qc.rx('+'-'*(gate=='rx(-pi/4)')+'np.pi/4,grid.qr['+qubit+'])'
                clean_command = 'qc.rx('+'-'*(gate=='rx(-pi/4)')+'np.pi/4,'+qubit_name+')'
            elif gate in ['cz','cx','swap']:
                real_command = (
                    f'grid.qc.{gate}(grid.qr['
                    + '0' * (qubit == '1')
                    + '1' * (qubit == '0')
                    + '],grid.qr['
                    + qubit
                    + '])'
                )
                clean_command = f'qc.{gate}' + '(' + other_name + ',' + qubit_name + ')'
            return [real_command,clean_command]

        bloch = [None]

        # set up initial state and figure
        if mode=='y':
            grid = pauli_grid(backend=backend,shots=shots,mode='line',y_boxes=True)
        else:
            grid = pauli_grid(backend=backend,shots=shots,mode=mode)

        self.initializer = []
        for gate in initialize:
            command = get_command(gate[0],gate[1])
            eval(command[0])
            self.initializer.append(command[1])

        required_gates = copy.deepcopy(allowed_gates)

        # determine which qubits to show in figure
        if allowed_gates['0']=={} : # if no gates are allowed for qubit 0, we know to only show qubit 1
                shown_qubit = 1
        elif allowed_gates['1']=={} : # and vice versa
                shown_qubit = 0
        else :
                shown_qubit = 2

        # show figure
        grid_view = _img()
        grid.update_grid(bloch=bloch[0],hidden=vi[0],qubit=vi[1],corr=vi[2],message=get_total_gate_list(),output=grid_view)
        display(grid_view.widget)



        description = {'gate':['Choose gate'],'qubit':['Choose '+'qu'*vi[1]+'bit'],'action':['Make it happen!']}

        all_allowed_gates_raw = []
        for q in ['0','1','both']:
            all_allowed_gates_raw += list(allowed_gates[q])
        all_allowed_gates_raw = list(set(all_allowed_gates_raw))

        all_allowed_gates = []
        for g in ['bloch']:
            if g in all_allowed_gates_raw:
                all_allowed_gates.append( g )
        for g in ['x','y','z','h','cz','cx']:
            if g in all_allowed_gates_raw:
                all_allowed_gates.append( g )
        for g in all_allowed_gates_raw:
            if g not in all_allowed_gates:
                all_allowed_gates.append( g )

        gate = widgets.ToggleButtons(options=description['gate']+all_allowed_gates)
        qubit = widgets.ToggleButtons(options=[''])
        action = widgets.ToggleButtons(options=[''])

        boxes = widgets.VBox([gate,qubit,action])
        display(boxes)
        self.program = []
        self.qubit_names = qubit_names

        def given_gate(a):
            # Action to be taken when gate is chosen. This sets up the system to choose a qubit.

            if not gate.value:
                return
            if gate.value in allowed_gates['both']:
                qubit.options = description['qubit'] + ["not required"]
                qubit.value = "not required"
            else:
                allowed_qubits = []
                for q in ['1','0']:
                    if (gate.value in allowed_gates[q]) or (gate.value in allowed_gates['both']):
                        allowed_qubits.append(q)
                allowed_qubit_names = []
                for q in allowed_qubits:
                    allowed_qubit_names += [qubit_names[q]]
                qubit.options = description['qubit'] + allowed_qubit_names

        def given_qubit(b):
            # Action to be taken when qubit is chosen. This sets up the system to choose an action.

            if qubit.value not in ['',description['qubit'][0],'Success!']:
                action.options = description['action']+['Apply operation']

        def given_action(c):
            # Action to be taken when user confirms their choice of gate and qubit.
            # This applied the command, updates the visualization and checks whether the puzzle is solved.

            if action.value in ['', description['action'][0]]:
                return
                # apply operation
            if action.value=='Apply operation':
                if qubit.value not in ['',description['qubit'][0],'Success!']:
                    # translate bit gates to qubit gates
                    if gate.value=='NOT':
                        q_gate = 'x'
                    elif gate.value=='CNOT':
                        q_gate = 'cx'
                    else:
                        q_gate = gate.value
                    q = qubit_names['1'] if qubit.value=="not required" else qubit.value
                    q01 = '0'*(qubit.value==qubit_names['0']) + '1'*(qubit.value==qubit_names['1']) + 'both'*(qubit.value=="not required")
                    if q_gate in ['bloch']:
                        bloch[0] = q01 if q01 != bloch[0] else None
                    else:
                        command = get_command(q_gate,q01)
                        eval(command[0])
                        self.program.append( command[1] )
                    if required_gates[q01][gate.value]>0:
                        required_gates[q01][gate.value] -= 1

                    grid.update_grid(bloch=bloch[0],hidden=vi[0],qubit=vi[1],corr=vi[2],message=get_total_gate_list(),output=grid_view)

            success = get_success(required_gates)
            if success:
                gate.options = ['Success!']
                qubit.options = ['Success!']
                action.options = ['Success!']
                plt.close(grid.fig)
            else:
                gate.value = description['gate'][0]
                qubit.options = ['']
                action.options = ['']

        gate.observe(given_gate)
        qubit.observe(given_qubit)
        action.observe(given_action)

    def get_circuit(self, use_initializer=False):

        q = QuantumRegister(2,'q')
        b = ClassicalRegister(2,'b')
        qc = QuantumCircuit(q,b)
                
        if '[' not in self.qubit_names['0']+self.qubit_names['0']:
            exec(self.qubit_names['0']+' = q[0]')
            exec(self.qubit_names['1']+' = q[1]')
            
        if use_initializer:
            for line in self.initializer:
                eval(line)

        for line in self.program:
            eval(line)

        return qc
    
    def plot_spheres(self):
        return plot_bloch_multivector(Statevector(self.get_circuit(use_initializer=True)),reverse_bits=True)

class pauli_grid():
    # Allows a quantum circuit to be created, modified and implemented, and visualizes the output in the style of 'Hello Quantum'.

    def __init__(self,backend=Aer.get_backend('qasm_simulator'),shots=1024,mode='circle',y_boxes=False):
        """
        backend=Aer.get_backend('qasm_simulator')
            Backend to be used by Qiskit to calculate expectation values (defaults to local simulator).
        shots=1024
            Number of shots used to to calculate expectation values.
        mode='circle'
            Either the standard 'Hello Quantum' visualization can be used (with mode='circle') or the alternative line based one (mode='line').
        y_boxes=True
            Whether to display full grid that includes Y expectation values.
        """

        self.backend = backend
        self.shots = shots

        self.y_boxes = y_boxes
        if self.y_boxes:
            self.box = {'IZ':(-1, 2), 'IX':(-3, 4), 'IY':(-2, 3),
                        'XI':( 3, 4), 'YI':( 2,3 ), 'ZI':( 1, 2),
                        'XZ':( 2, 5), 'YZ':( 1, 4), 'ZZ':( 0, 3),
                        'XX':( 0, 7), 'YX':(-1, 6), 'ZX':(-2, 5), 
                        'XY':( 1, 6), 'YY':( 0, 5), 'ZY':(-1, 4)}
        else:
            self.box = {'IZ':(-1, 2),'IX':(-2, 3),
                        'ZI':( 1, 2),'XI':( 2, 3),
                        'XZ':( 1, 4),'ZZ':( 0, 3),
                        'ZX':(-1, 4),'XX':( 0, 5)}

        self.rho = {pauli: 0.0 for pauli in self.box}
        for pauli in ['ZI','IZ','ZZ']:
            self.rho[pauli] = 1.0

        self.qr = QuantumRegister(2)
        self.cr = ClassicalRegister(2)
        self.qc = QuantumCircuit(self.qr, self.cr)

        self.mode = mode

        figsize = (5, 5) if self.mode!='y' else (6, 6)
        self.fig = plt.figure(figsize=(6,6),facecolor=background_color)
        self.ax = self.fig.add_subplot(111)
        plt.axis('off')

        self.bottom = self.ax.text(-3,1,"",size=10,va='top',color='black')

        self.points = {}
        for pauli, value in self.box.items():
            self.points[pauli] = [ self.ax.add_patch( Circle(self.box[pauli], 0.0, color=point_color[0], zorder=10) ) ]
            self.points[pauli].append(
                self.ax.add_patch(
                    Circle(value, 0.0, color=point_color[1], zorder=10)
                )
            )

        self.initial = True

    def get_rho(self):
        # Runs the circuit specified by self.qc and determines the expectation values for 'ZI', 'IZ', 'ZZ', 'XI', 'IX', 'XX', 'ZX' and 'XZ' (and the ones with Ys too if needed).

        if self.y_boxes:
            corr = ['ZZ','ZX','XZ','XX','YY','YX','YZ','XY','ZY']
            ps = ['X','Y','Z']
        else:
            corr = ['ZZ','ZX','XZ','XX']
            ps = ['X','Z']


        self.rho = {}

        results = {}
        for basis in corr:
            temp_qc = copy.deepcopy(self.qc)
            for j in range(2):
                if basis[j]=='X':
                    temp_qc.h(self.qr[j])
                elif basis[j]=='Y':
                    temp_qc.sdg(self.qr[j])
                    temp_qc.h(self.qr[j])

            if self.backend is None:
                ket = Statevector([1,0,0,0])
                ket = ket.from_instruction(temp_qc)
                results[basis] = ket.probabilities_dict()
            else:     
                temp_qc.barrier(self.qr)
                temp_qc.measure(self.qr,self.cr)
                job = execute(temp_qc, backend=self.backend, shots=self.shots)
                results[basis] = job.result().get_counts()
                for string in results[basis]:
                    results[basis][string] = results[basis][string]/self.shots

        prob = {}
        # prob of expectation value -1 for single qubit observables
        for j in range(2):

            for p in ps:
                pauli = {pp: (j==1)*pp + p + (j==0)*pp for pp in ['I']+ps}
                prob[pauli['I']] = 0
                for ppp in ps:
                    basis = pauli[ppp]
                    for string in results[basis]:
                        if string[(j+1)%2]=='1':
                            prob[pauli['I']] += results[basis][string]/(2+self.y_boxes)

        # prob of expectation value -1 for two qubit observables
        for basis in corr:
            prob[basis] = 0
            for string in results[basis]:
                if string[0]!=string[1]:
                    prob[basis] += results[basis][string]

        for pauli in prob:
            self.rho[pauli] = 1-2*prob[pauli]
             
            
            
        

    def update_grid(self,rho=None,labels=False,bloch=None,hidden=[],qubit=True,corr=True,message="",output=None):
        """
        rho = None
            Dictionary of expectation values for 'ZI', 'IZ', 'ZZ', 'XI', 'IX', 'XX', 'ZX' and 'XZ'. If supplied, this will be visualized instead of the results of running self.qc.
        labels = False
            Determines whether basis labels are printed in the corresponding boxes.
        bloch = None
            If a qubit name is supplied, and if mode='line', Bloch circles are displayed for this qubit
        hidden = []
            Which qubits have their circles hidden (empty list if both shown).
        qubit = True
            Whether both circles shown for each qubit (use True for qubit puzzles and False for bit puzzles).
        corr = True
            Whether the correlation circles (the four in the middle) are shown.
        message
            A string of text that is displayed below the grid.
        """

        def see_if_unhidden(pauli):
            # For a given Pauli, see whether its circle should be shown.

            unhidden = True
            # first: does it act non-trivially on a qubit in `hidden`
            for j in hidden:
                unhidden = unhidden and (pauli[j]=='I')
            # second: does it contain something other than 'I' or 'Z' when only bits are shown
            if qubit==False:
                for j in range(2):
                    unhidden = unhidden and (pauli[j] in ['I','Z'])
            # third: is it a correlation pauli when these are not allowed
            if corr==False:
                unhidden = unhidden and ((pauli[0]=='I') or (pauli[1]=='I'))
            # finally: is it actually in rho
            unhidden = unhidden and (pauli in self.rho)
            return unhidden

        def add_line(line,pauli_pos,pauli):
            """
            For mode='line', add in the line.

            line = the type of line to be drawn (X, Z or the other one)
            pauli = the box where the line is to be drawn
            expect = the expectation value that determines its length
            """

            delta = 0.07

            unhidden = see_if_unhidden(pauli)
            p = (1-self.rho[pauli])/2 # prob of 1 output
            # in the following, white lines goes from a to b, and black from b to c
            if unhidden:
                if line=='X':

                    a = ( self.box[pauli_pos][0]-length/2, self.box[pauli_pos][1]-width/2 )
                    c = ( self.box[pauli_pos][0]+length/2, self.box[pauli_pos][1]-width/2 )
                    b = ( p*a[0] + (1-p)*c[0] , p*a[1] + (1-p)*c[1] )

                    self.ax.add_patch( Rectangle( a, length*(1-p), width, angle=0, color=line_color[0]) )
                    self.ax.add_patch( Rectangle( b, length*p, width, angle=0, color=line_color[2]) )
                    if length*p>delta:
                        self.ax.add_patch( Rectangle( (b[0]+delta/2,b[1]+delta*0.6), length*p-delta, width-delta, angle=0, color=line_color[1]) )

                elif line=='Z':

                    a = ( self.box[pauli_pos][0]-width/2, self.box[pauli_pos][1]-length/2 )
                    c = ( self.box[pauli_pos][0]-width/2, self.box[pauli_pos][1]+length/2 )
                    b = ( p*a[0] + (1-p)*c[0] , p*a[1] + (1-p)*c[1] )

                    self.ax.add_patch( Rectangle( a, width, length*(1-p), angle=0, color=line_color[0]) )
                    self.ax.add_patch( Rectangle( b, width, length*p, angle=0, color=line_color[2]) )
                    if length*p>delta:
                        self.ax.add_patch( Rectangle( (b[0]+delta/2,b[1]+delta/2), width-delta, length*p-delta, angle=0, color=line_color[1]) )

                else:


                    a = ( self.box[pauli_pos][0]-length/(2*np.sqrt(2)), self.box[pauli_pos][1]-length/(2*np.sqrt(2)) )
                    c = ( self.box[pauli_pos][0]+length/(2*np.sqrt(2)), self.box[pauli_pos][1]+length/(2*np.sqrt(2)) )
                    b = ( p*a[0] + (1-p)*c[0] , p*a[1] + (1-p)*c[1] )

                    self.ax.add_patch( Rectangle( a, width, length*(1-p), angle=-45, color=line_color[0]) )
                    self.ax.add_patch( Rectangle( b, width, length*p, angle=-45, color=line_color[2]) )
                    if length*p>delta:
                        self.ax.add_patch( Rectangle( (b[0]+delta*np.sqrt(2)/2,b[1]+delta*0.1*np.sqrt(2)/2), width-delta, length*p-delta, angle=-45, color=line_color[1]) )

            return p

        L = 0.98*np.sqrt(2) # box height and width
        length = 0.75*L # line length
        width = 0.12*L # line width
        r = 0.6 # circle radius

        # set the state
        self.rho = rho
        if self.rho == {} or self.rho is None:
            self.get_rho()

        # draw boxes
        if self.initial:
            for pauli in self.box:
                color = box_color[0] if 'I' in pauli else box_color[1]
                self.ax.add_patch( Rectangle( (self.box[pauli][0],self.box[pauli][1]-1), L, L, angle=45, color=color) )

        # draw circles
        for pauli in self.box:
            unhidden = see_if_unhidden(pauli)
            if unhidden:
                if self.mode!='line':
                    prob = (1-self.rho[pauli])/2
                    color=(prob,prob,prob) 
                    self.ax.add_patch( Circle(self.box[pauli], r, color=color) )
                else:
                    if 'Y' in pauli:
                        self.ax.add_patch( Circle(self.box[pauli], r, color=circle_color[1]) )
                    else:
                        self.ax.add_patch( Circle(self.box[pauli], r, color=circle_color[0]) )

        # hide points
        for pauli in self.points:
            for point in self.points[pauli]:
                point.radius = 0

        # update bars if required
        if self.mode=='line':
            if bloch in ['0','1']:
                for other in 'IXZ':
                    px = other*(bloch=='1') + 'X' + other*(bloch=='0')
                    pz = other*(bloch=='1') + 'Z' + other*(bloch=='0')
                    prob_z = add_line('Z',pz,pz)
                    prob_x = add_line('X',pz,px)
                    for j,point in enumerate(self.points[pz]):
                        if see_if_unhidden(pz):
                            point.center = (self.box[pz][0]-(prob_x-0.5)*length, self.box[pz][1]-(prob_z-0.5)*length)
                            point.radius = (j==0)*0.05 + (j==1)*0.04
                px = 'I'*(bloch=='0') + 'X' + 'I'*(bloch=='1')
                pz = 'I'*(bloch=='0') + 'Z' + 'I'*(bloch=='1')
                add_line('Z',pz,pz)
                add_line('X',px,px)
                if self.y_boxes:
                    for pauli in ['IY','YI','XY','YX','ZY','YZ','YY']:
                        add_line('ZXY',pauli,pauli)
            else:
                for pauli in self.box:
                    for point in self.points[pauli]:
                        point.radius = 0.0
                    if pauli in ['ZI','IZ','ZZ']:
                        add_line('Z',pauli,pauli)
                    if pauli in ['XI','IX','XX']:
                        add_line('X',pauli,pauli)
                    if pauli in ['XZ','ZX']+self.y_boxes*['IY','YI','XY','YX','ZY','YZ','YY']:
                        add_line('ZXY',pauli,pauli)

        self.bottom.set_text(message)

        if labels:
            for pauli in self.box:
                plt.text(self.box[pauli][0]-0.18,self.box[pauli][1]-0.85, pauli)

        if self.y_boxes:
            self.ax.set_xlim([-4,4])
            self.ax.set_ylim([0,8])
        else:
            self.ax.set_xlim([-3,3])
            self.ax.set_ylim([0,6])

        if output is None:
            self.fig.canvas.draw()
        else:
            plt.close() # prevent the graphic from showing inline
            output.value = self.fig

        self.initial = False
