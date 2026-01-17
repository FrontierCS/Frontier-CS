#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

struct Instruction {
    string type; // "POP" or "HALT"
    int a;       // if POP: value to match. if HALT: unused
    int x;       // goto if match/halt
    int b;       // push value
    int y;       // goto else
};

vector<Instruction> program;
int add_instruction(string type, int a, int x, int b, int y) {
    program.push_back({type, a, x, b, y});
    return program.size();
}

const int UNKNOWN = -1;

struct Layer {
    string type; // "Base", "Linear", "Double7", "Double9"
    int val_in;  // Value expected on stack
    int val_aux; // Second value for Double
    int val_garbage; // Garbage value
    int entry_instr;
    int return_target; // Where this layer returns to (in parent)
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    long long k;
    if (!(cin >> k)) return 0;

    if (k == 1) {
        cout << "1\nHALT PUSH 1 GOTO 1\n";
        return 0;
    }

    // We construct a program that executes Preamble + Body + Halt.
    // Preamble takes 1 step. Halt takes 1 step.
    // So Body needs to take t = k - 2 steps.
    long long t = k - 2;
    
    // Decompose t into layers
    vector<string> layer_types;
    
    // While t is large enough to use Double block (min cost 9)
    while (t >= 9) {
        // If t % 4 == 1, then (t - 7)/2 is odd. Use Double7.
        // If t % 4 == 3, then (t - 9)/2 is odd. Use Double9.
        if (t % 4 == 1) {
            layer_types.push_back("Double7");
            t = (t - 7) / 2;
        } else {
            layer_types.push_back("Double9");
            t = (t - 9) / 2;
        }
    }
    
    // Remaining t < 9. Must be odd.
    // Use Linear blocks (+2 steps) to reduce to Base (1 step).
    while (t > 1) {
        layer_types.push_back("Linear");
        t -= 2;
    }
    layer_types.push_back("Base");
    
    // We want the vector to be [Base, Linear, ..., Outermost]
    reverse(layer_types.begin(), layer_types.end());
    
    // Assign values
    int current_val = 1;
    vector<Layer> layers(layer_types.size());
    // Assign from Outermost to Innermost so values are consistent?
    // Actually order doesn't matter as long as values are distinct.
    for (int i = layer_types.size() - 1; i >= 0; --i) {
        layers[i].type = layer_types[i];
        layers[i].val_in = current_val++;
        if (layers[i].type == "Double7" || layers[i].type == "Double9") {
            layers[i].val_aux = current_val++;
            layers[i].val_garbage = current_val++;
        }
    }
    
    int next_instr = 1; 
    
    // Preamble
    int preamble_idx = next_instr++;
    add_instruction("HALT", 0, 0, 0, 0); 
    
    // Final Halt
    int final_halt_idx = next_instr++;
    add_instruction("HALT", 0, 0, 1, 1);
    
    // Generate code for layers (Innermost first)
    for (int i = 0; i < layers.size(); ++i) {
        int child_entry = (i > 0) ? layers[i-1].entry_instr : -1;
        
        if (layers[i].type == "Base") {
            layers[i].entry_instr = next_instr++;
            add_instruction("POP", layers[i].val_in, UNKNOWN, layers[i].val_in, UNKNOWN);
        }
        else if (layers[i].type == "Linear") {
            int start_idx = next_instr++;
            layers[i].entry_instr = start_idx;
            // PUSH child_val GOTO Child_Entry
            add_instruction("POP", layers[i].val_in, UNKNOWN, layers[i-1].val_in, child_entry);
            
            int check_idx = next_instr++;
            add_instruction("POP", layers[i].val_in, UNKNOWN, 1, 1);
            
            program[start_idx-1].x = check_idx;
            layers[i-1].return_target = check_idx;
        }
        else { // Double7 or Double9
            int X = layers[i].val_in;
            int Y = layers[i].val_aux;
            int G = layers[i].val_garbage;
            int child_val = layers[i-1].val_in;
            
            int start_idx = next_instr++;
            layers[i].entry_instr = start_idx;
            
            int check_idx = next_instr++;
            int swap_idx = next_instr++;
            int pass2_idx = next_instr++;
            int cleanup_idx = next_instr++;
            int finish_idx = next_instr++;
            
            int delay_idx = -1, restore_idx = -1;
            if (layers[i].type == "Double9") {
                delay_idx = next_instr++;
                restore_idx = next_instr++;
            }
            
            int else_target = (layers[i].type == "Double9") ? delay_idx : cleanup_idx;
            
            add_instruction("POP", Y, check_idx, child_val, child_entry); // Start
            add_instruction("POP", X, swap_idx, G, else_target);          // Check
            add_instruction("HALT", 0, 0, Y, pass2_idx);                  // Swap
            add_instruction("POP", X, 0, child_val, child_entry);         // Pass2
            add_instruction("POP", G, finish_idx, 0, 0);                  // Cleanup
            add_instruction("POP", Y, UNKNOWN, 0, 0);                     // Finish
            
            if (layers[i].type == "Double9") {
                add_instruction("POP", G, restore_idx, 0, 0);             // Delay
                add_instruction("HALT", 0, 0, G, cleanup_idx);            // Restore
            }
            
            layers[i-1].return_target = check_idx;
        }
    }
    
    // Fix Preamble
    int outer_layer_idx = layers.size() - 1;
    program[preamble_idx-1].b = layers[outer_layer_idx].val_in;
    program[preamble_idx-1].y = layers[outer_layer_idx].entry_instr;
    
    // Fix Return Targets
    for (int i = 0; i < layers.size(); ++i) {
        int target = (i == layers.size() - 1) ? final_halt_idx : layers[i+1].return_target;
        int instr_to_fix = -1;
        if (layers[i].type == "Base") {
            instr_to_fix = layers[i].entry_instr;
            program[instr_to_fix-1].x = target;
        } else if (layers[i].type == "Linear") {
            instr_to_fix = layers[i].entry_instr + 1;
            program[instr_to_fix-1].x = target;
        } else {
            instr_to_fix = layers[i].entry_instr + 5;
            program[instr_to_fix-1].x = target;
        }
    }

    cout << program.size() << "\n";
    for (const auto& instr : program) {
        if (instr.type == "HALT") {
            cout << "HALT PUSH " << instr.b << " GOTO " << instr.y << "\n";
        } else {
            cout << "POP " << instr.a << " GOTO " << instr.x << " PUSH " << instr.b << " GOTO " << instr.y << "\n";
        }
    }

    return 0;
}