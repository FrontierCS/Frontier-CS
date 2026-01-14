#include <iostream>
#include <vector>
#include <string>
#include <map>

using namespace std;

struct Instruction {
    string type; // "POP" or "HALT"
    int a;       // only for POP
    int x;       // goto x
    int b;       // push b
    int y;       // goto y
};

vector<Instruction> program;
int add_instruction(string type, int a, int x, int b, int y) {
    program.push_back({type, a, x, b, y});
    return program.size();
}

// Placeholders for jumps
struct JumpRef {
    int instr_idx;
    bool is_x; // true if fixing x, false if fixing y
};
vector<JumpRef> pending_jumps;

// We need to resolve labels
// Map from label_id to instruction index
map<int, int> labels;

int get_label_addr(int id) {
    return labels[id];
}

void set_label(int id, int addr) {
    labels[id] = addr;
}

// Logic for level j
// We have levels 0 to 29.
// Each level j has:
//   Start_0 (Entry for state 0)
//   Start_1 (Entry for state 1)
//   Mid_0 (Return point from child for state 0)
//   Point_0_Switch (Transition 0->1)
//   Mid_1 (Return point from child for state 1)
//   Exit_0 (Dispatcher) -- actually exit logic is shared or sequenced
//   Wait, Exit logic is part of the flow.
//   We need distinct return points for child calls.

// Params for Level j
struct Level {
    long long cost;
    int val_0;
    int val_1;
    // Labels
    int label_start_0;
    int label_mid_0;   // Return from first child call
    int label_point_1; // Start of state 1 flow
    int label_mid_1;   // Return from second child call
    int label_end;     // Exit dispatcher
};

Level levels[31];
// Main callers need markers
struct MainCall {
    int level_idx;
    int marker;
    int return_label;
};
vector<MainCall> main_calls;

int main() {
    long long K;
    if (!(cin >> K)) return 0;

    if (K == 1) {
        cout << "1\nHALT PUSH 1 GOTO 1" << endl;
        return 0;
    }

    // Costs: W_j = 7 * 2^j - 5
    // j from 0 to 29
    for (int j = 0; j <= 29; ++j) {
        levels[j].cost = (7LL << j) - 5;
        levels[j].val_0 = 2 * j + 1;
        levels[j].val_1 = 2 * j + 2;
        levels[j].label_start_0 = 1000 * j + 1;
        levels[j].label_mid_0 = 1000 * j + 2;
        levels[j].label_point_1 = 1000 * j + 3;
        levels[j].label_mid_1 = 1000 * j + 4;
        levels[j].label_end = 1000 * j + 5;
    }

    // Decompose K-1
    long long target = K - 1;
    vector<int> blocks;
    // Greedy decomposition
    // Since we only have W_0=2 (even) and others odd, we need to be careful with parity.
    // However, since we can pick W_0 multiple times, and W_1... are odd.
    // Actually, we can just use small blocks for small values.
    // But W_0=2 is the only even block.
    // If target is odd, we MUST use at least one odd block.
    // If target is even, we can use 0 odd blocks or even number of odd blocks.
    
    while (target > 0) {
        int best_j = -1;
        for (int j = 29; j >= 0; --j) {
            if (levels[j].cost <= target) {
                // Check parity constraint?
                // If we take this block, new_target = target - cost.
                // We need to be able to solve new_target.
                // If new_target is odd, we need at least one odd block <= new_target.
                // Smallest odd is W_1 = 9.
                // If new_target is odd and < 9, we are stuck (can't represent 1,3,5,7).
                // Note: W_0=2.
                // So "bad" states are odd numbers < 9.
                long long rem = target - levels[j].cost;
                if (rem % 2 != 0 && rem < 9) {
                    continue; // Don't take this
                }
                best_j = j;
                break;
            }
        }
        if (best_j == -1) {
            // Should not happen given 2 and 9 cover everything eventually
            // But for very small odd target < 9? 
            // Initial K is odd => target K-1 is even.
            // If we maintain target even, we pick even blocks? Only W_0=2.
            // If we pick odd block, target becomes odd. Then we pick another odd block -> even.
            // Just need to avoid remainder being small odd.
            // If we are stuck, it's logic error.
            break; 
        }
        blocks.push_back(best_j);
        target -= levels[best_j].cost;
    }

    // Assign markers for main calls
    int marker_counter = 600; 
    for (int b : blocks) {
        MainCall mc;
        mc.level_idx = b;
        mc.marker = marker_counter++;
        mc.return_label = marker_counter++; // Label ID for return point
        main_calls.push_back(mc);
    }

    // 1. Generate Main Loop
    int main_start_label = 90000;
    set_label(main_start_label, program.size() + 1);
    
    // Initial Push Marker 0 (Dummy) ? No, main calls structure:
    // PUSH Marker -> Call -> Ret -> Next
    
    // But first instruction must be special?
    // "The interpreter starts... reads the first instruction."
    // Input K>1. First instr: POP ... PUSH b GOTO y.
    // Stack empty -> Pushes b, GOTO y.
    
    // We will structure main as:
    // Instr 1: POP 999 GOTO Halt_Label PUSH First_Marker GOTO First_Call_Start
    // The "POP 999" is just dummy to force PUSH branch initially.
    // But wait, after first block returns, we are at Return_Label.
    // We need to proceed to next block.
    
    // Let's chain them.
    // Block 0: Push Marker0, Goto Start_Block0.
    // Return_Point_0: Push Marker1, Goto Start_Block1.
    // ...
    // Last Return Point: HALT.
    
    // Instruction 1 must coincide with start of Block 0 logic.
    // Instr 1: POP Dummy GOTO ... PUSH M0 GOTO Start0.
    
    int dummy_pop = 999;
    
    // We need to setup the main chain labels
    for (size_t i = 0; i < main_calls.size(); ++i) {
        int lvl = main_calls[i].level_idx;
        int m = main_calls[i].marker;
        int ret_lbl = main_calls[i].return_label;
        int start_lbl = levels[lvl].label_start_0;
        
        // The instruction that calls this block:
        // If i == 0, this is the entry point (Index 1).
        // It fails POP (stack empty), Pushes Marker, Jumps to Level Start.
        // If i > 0, we arrive here from previous return.
        // We define the label for this point as previous return label.
        
        if (i > 0) {
            set_label(main_calls[i-1].return_label, program.size() + 1);
            // This instruction is executed after previous block returns.
            // Previous block popped its marker. Stack is empty?
            // Wait. Main stack logic:
            // Empty -> Push M0 -> Run -> Pop M0 -> Empty.
            // So stack is empty here.
            // We need to Push M1 and run.
            // So: POP Dummy GOTO ... PUSH M1 GOTO Start1.
            add_instruction("POP", dummy_pop, 0, m, 0); 
            // Jump fixups later. x is unused (never popped dummy).
            // y is start_lbl.
            pending_jumps.push_back({(int)program.size()-1, false}); // fix y
            // Map the jump to start_lbl
             // Actually we can just store the target label id in pending
             // But we need a separate struct or reuse.
             // Let's just resolve y = get_label_addr(start_lbl) later.
             // We'll store label ID in y temporarily? No, y is int.
             program.back().y = start_lbl; // Store ID, resolve later
        } else {
            // First instruction
            add_instruction("POP", dummy_pop, 0, m, 0);
            program.back().y = start_lbl;
            // The jump x is irrelevant as stack empty. 
            // But to be valid, x must point somewhere. Point to 1.
            program.back().x = 1; 
        }
    }
    
    // Halt logic
    if (!main_calls.empty()) {
        set_label(main_calls.back().return_label, program.size() + 1);
    } else {
        // Should not happen for K > 1
    }
    // Final instruction: HALT
    int halt_idx = program.size() + 1;
    add_instruction("HALT", 0, 0, 1, halt_idx); // args ignored except PUSH/GOTO if stack non-empty (won't happen)
    program.back().y = halt_idx; // Self loop if not empty

    // 2. Generate Levels 0..29
    for (int j = 0; j <= 29; ++j) {
        Level& L = levels[j];
        
        // Start 0
        set_label(L.label_start_0, program.size() + 1);
        if (j == 0) {
            // Level 0 State 0: Cost 2.
            // Start: POP V_00 GOTO Push1 ... (Fail check) -> PUSH V_01 GOTO Mid
            // Actually POP fails on V_00? No, Start expects V_00.
            // We want to consume 1 step and switch to V_01.
            // So we need POP to FAIL.
            // POP (!V_00) ... PUSH V_01 GOTO Mid
            add_instruction("POP", L.val_1, 0, L.val_1, 0); // Check V_01 (Top is V_00). Fail. Push V_01.
            program.back().x = 1; // Dummy
            program.back().y = L.label_mid_0; // Goto Mid (which handles V_01)
        } else {
            // Level j > 0 State 0
            // Push (j-1)_0, Goto Start (j-1)_0
            // POP V_j1 (Fail) PUSH V_(j-1)0 GOTO Start_(j-1)0
            add_instruction("POP", L.val_1, 0, levels[j-1].val_0, 0);
            program.back().x = 1;
            program.back().y = levels[j-1].label_start_0;
        }

        // Mid 0 (Return from child 1)
        set_label(L.label_mid_0, program.size() + 1);
        if (j == 0) {
            // Level 0 State 1 (at Mid): Cost 1 step to pop and exit.
            // POP V_01 GOTO Exit
            add_instruction("POP", L.val_1, 0, 1, 0); // Pop success.
            program.back().x = L.label_end;
            program.back().y = 1; // Dummy
        } else {
            // Level j > 0: Returned from (j-1)_0. Stack is V_j0.
            // Switch to V_j1.
            // POP V_j0 GOTO Push1 ...
            // Push1: PUSH V_j1 GOTO Point1
            
            // Instruction at label_mid_0:
            add_instruction("POP", L.val_0, 0, L.val_1, 0); // Pop V_j0. Success.
            // Goto Push1. Push1 is next instruction.
            program.back().x = program.size() + 2; 
            program.back().y = 1; // Dummy

            // Push1
            add_instruction("PUSH", L.val_1, 0, 0, 0); // Push V_j1
            program.back().y = L.label_point_1;
            program.back().x = 1; // Dummy (PUSH type uses HALT format? No, PUSH is ELSE of POP or Explicit?)
            // Wait, "POP a GOTO x PUSH b GOTO y".
            // To just PUSH, we need condition to fail.
            // But here we arrived from successful POP V_j0.
            // So stack is whatever below V_j0 (Val of caller).
            // We want to Push V_j1.
            // We can check POP (Caller)? No caller varies.
            // Check POP (Impossible Value)?
            // Val is <= 1024. Use 1025? No limit 1024.
            // Use something we know is not there?
            // Caller val is V_j+1 or Marker.
            // V_j0 is 2j+1.
            // We can check POP V_j0 again? It was just popped.
            // So check POP V_j0. Will fail.
            // Else Push V_j1 Goto Point1.
            
            // Modify previous instruction to jump here?
            // No, the previous was "POP V_j0 GOTO x".
            // At x, stack has Caller Val.
            // We put "POP V_j0 ..." at x.
            
            // Re-write Mid 0 logic:
            // Instr 1 (Mid0): POP V_j0 GOTO Instr2 PUSH ... (Dummy).
            // Instr 2: POP V_j0 (Fail) GOTO ... PUSH V_j1 GOTO Point1.
            
            // Correct.
            // But wait, can we combine?
            // We want: Pop V_j0, Push V_j1, Goto Point1.
            // Is it possible in 1 instr?
            // "POP a ... PUSH b ..." -> Pop a if match, Push b if not.
            // Cannot do both.
            // So 2 instructions needed.
            
            // Correct code at program.back().x (Next instr):
            int instr2_idx = program.size() + 1;
            // Previous instr already points x to instr2_idx.
            add_instruction("POP", L.val_0, 0, L.val_1, 0);
            program.back().x = 1; // Should not happen
            program.back().y = L.label_point_1;
        }

        if (j > 0) {
            // Point 1 (Start of second child call)
            set_label(L.label_point_1, program.size() + 1);
            // Stack has V_j1.
            // Push (j-1)_0. Goto Start (j-1)_0.
            // POP V_j0 (Fail) PUSH (j-1)_0 ...
            add_instruction("POP", L.val_0, 0, levels[j-1].val_0, 0);
            program.back().x = 1;
            program.back().y = levels[j-1].label_start_0;

            // Mid 1 (Return from second child call)
            set_label(L.label_mid_1, program.size() + 1);
            // Stack has V_j1.
            // Pop V_j1. Goto End.
            add_instruction("POP", L.val_1, 0, 1, 0);
            program.back().x = L.label_end;
            program.back().y = 1;
        }

        // Exit Dispatcher
        set_label(L.label_end, program.size() + 1);
        // We need to check callers.
        // List of Callers:
        // 1. Level j+1 (if j<29). It calls from State 0 and State 1.
        //    State 0 of j+1 expects return to Mid_0 of j+1.
        //    State 1 of j+1 expects return to Mid_1 of j+1.
        //    Caller 0 val: V_(j+1)0. Caller 1 val: V_(j+1)1.
        // 2. Main Calls.
        
        vector<pair<int, int>> dispatch_targets;
        if (j < 29) {
            dispatch_targets.push_back({levels[j+1].val_0, levels[j+1].label_mid_0});
            dispatch_targets.push_back({levels[j+1].val_1, levels[j+1].label_mid_1});
        }
        for (const auto& mc : main_calls) {
            if (mc.level_idx == j) {
                dispatch_targets.push_back({mc.marker, mc.return_label});
            }
        }
        
        // Generate chain of checks
        // Each check: POP Val GOTO Restore PUSH Val GOTO NextCheck
        // Restore: PUSH Val GOTO Target
        // We can optimize Restore:
        // POP Val GOTO Target ...
        // But Target expects Val on stack!
        // If we POP Val, we remove it.
        // We need to jump to a PUSH.
        // "POP Val GOTO Restore ..."
        // Restore: "POP (Dummy) GOTO ... PUSH Val GOTO Target"
        
        for (size_t k = 0; k < dispatch_targets.size(); ++k) {
            int val = dispatch_targets[k].first;
            int tgt = dispatch_targets[k].second;
            
            // Check instruction
            int check_idx = program.size() + 1;
            int restore_idx = check_idx + 1;
            int next_check_idx = check_idx + 2;
            
            // Last one doesn't need next check (assumed guaranteed match)
            
            add_instruction("POP", val, 0, val, 0);
            program.back().x = restore_idx;
            program.back().y = (k == dispatch_targets.size() - 1) ? 1 : next_check_idx;
            
            // Restore instruction
            add_instruction("POP", dummy_pop, 0, val, 0); // Pop dummy(fail) -> Push val -> Goto Tgt
            program.back().x = 1;
            program.back().y = tgt;
        }
    }

    // Resolve Labels
    cout << program.size() << endl;
    for (const auto& instr : program) {
        int final_x = instr.x;
        int final_y = instr.y;
        
        // If x or y looks like a label ID (large number), resolve it
        if (final_x >= 1000) final_x = get_label_addr(final_x);
        if (final_y >= 1000) final_y = get_label_addr(final_y);
        
        if (instr.type == "HALT") {
            cout << "HALT PUSH " << instr.b << " GOTO " << final_y << endl;
        } else {
            cout << "POP " << instr.a << " GOTO " << final_x << " PUSH " << instr.b << " GOTO " << final_y << endl;
        }
    }

    return 0;
}