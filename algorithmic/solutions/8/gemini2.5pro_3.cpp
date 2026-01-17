#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// A simple struct to hold instruction details.
struct Instruction {
    string type;
    int a, x, b, y;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    unsigned int k;
    cin >> k;

    if (k == 1) {
        cout << 1 << endl;
        cout << "HALT PUSH 1 GOTO 1" << endl;
        return 0;
    }

    unsigned int m = (k - 1) / 2;

    vector<Instruction> program;
    int n = 0;

    // Entry point: instruction 1
    // The stack is empty. This instruction pushes a special marker (1020)
    // to signify an empty initial counter and transfers control to the
    // first bit-processing block (for bit 30).
    program.push_back({"POP", 1023, 2, 1020, 2});
    n = 1;

    // Generate 31 blocks of instructions, one for each bit of M from 30 down to 0.
    for (int i = 30; i >= 0; --i) {
        bool bit_is_one = (m >> i) & 1;
        
        int current_block_start = n + 1;
        int next_block_start;
        if (i > 0) {
            next_block_start = current_block_start + 6;
        } else {
            // After processing bit 0, jump to the main execution loop.
            next_block_start = 1 + 31 * 6 + 1; 
        }

        // Define distinct symbols for items at each stage to avoid conflicts.
        // `val_in_prev_stage`: Symbol from the previous stage (or initial marker).
        // `val_out_current_stage`: Symbol this stage will produce.
        // `val_temp`: Temporary symbol used during the doubling process.
        int val_in_prev_stage = (i == 30) ? 1020 : (2 * (i + 1) + 3);
        int val_out_current_stage = (i == 0) ? 3 : (2 * i + 3);
        int val_temp = 2 * i + 4;

        // --- Block for bit i ---
        // Part 1: Doubling (converts each val_in_prev_stage to two val_temp)
        // D1: Pop an item from the previous stage. If none, go to the Adder part.
        program.push_back({"POP", val_in_prev_stage, current_block_start + 1, 1021, current_block_start + 3});
        // D2 & D3: Push two temporary items. Then loop back to D1.
        program.push_back({"POP", 1023, current_block_start + 2, val_temp, current_block_start + 2});
        program.push_back({"POP", 1023, current_block_start, val_temp, current_block_start});
        
        // Part 2: Adder (conditionally adds one item if bit is 1)
        int adder_target = current_block_start + 4;
        if (bit_is_one) {
            // If m_i is 1, push one new item. The POP on 1021 will fail.
            program.push_back({"POP", 1021, adder_target, val_out_current_stage, adder_target});
        } else {
            // If m_i is 0, just pass control.
            program.push_back({"POP", 1021, adder_target, 1021, adder_target});
        }

        // Part 3: Conversion (converts each val_temp back to val_out_current_stage)
        // C1: Pop a temporary item. If none, go to the next bit's block.
        program.push_back({"POP", val_temp, current_block_start + 5, 1021, next_block_start});
        // C2: Push one final item. Loop back to C1.
        program.push_back({"POP", 1023, current_block_start + 4, val_out_current_stage, current_block_start + 4});

        n += 6;
    }
    
    // Main loop: runs for 2*M steps.
    int loop_entry = n + 1;
    int halt_instr = n + 2;
    // The symbol for the final counter items is 3.
    program.push_back({"POP", 3, halt_instr, 2, loop_entry});
    program.push_back({"HALT", -1, -1, 1, loop_entry});
    n += 2;

    cout << n << endl;
    for (const auto& instr : program) {
        if (instr.type == "POP") {
            cout << "POP " << instr.a << " GOTO " << instr.x << " PUSH " << instr.b << " GOTO " << instr.y << endl;
        } else { // HALT
            cout << "HALT PUSH " << instr.b << " GOTO " << instr.y << endl;
        }
    }

    return 0;
}