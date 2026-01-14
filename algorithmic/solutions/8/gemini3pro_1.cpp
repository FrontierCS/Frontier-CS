#include <iostream>
#include <vector>
#include <string>

using namespace std;

struct Instruction {
    string type;
    int a, x, b, y;
};

long long k;
vector<Instruction> program;

void add_inst(string type, int a, int x, int b, int y) {
    program.push_back({type, a, x, b, y});
}

// Helper to get current instruction index (1-based)
int current_idx() {
    return program.size() + 1;
}

int main() {
    if (cin >> k) {}
    
    if (k == 1) {
        cout << "1" << endl;
        cout << "HALT PUSH 1 GOTO 1" << endl;
        return 0;
    }

    // Target cost W = k - 1
    // Costs: C_0 = 2, C_i = 2*C_{i-1} + 6
    long long W = k - 1;
    
    // Determine number of layers m
    vector<long long> min_costs;
    long long curr = 2;
    min_costs.push_back(curr);
    while (true) {
        long long next_c = 2 * curr + 6;
        if (next_c > W) break;
        min_costs.push_back(next_c);
        curr = next_c;
    }
    
    int m = min_costs.size() - 1;
    
    vector<long long> layer_costs(m + 1);
    vector<long long> k_waste(m + 1);
    
    layer_costs[m] = W;
    for (int i = m; i >= 1; --i) {
        long long target = (layer_costs[i] - 6) / 2;
        if (target % 2 != 0) target--;
        layer_costs[i-1] = target;
        k_waste[i] = (layer_costs[i] - 6 - 2 * layer_costs[i-1]) / 2;
    }
    k_waste[0] = (layer_costs[0] - 2) / 2;

    // Inst 1: HALT ...
    add_inst("HALT", 0, 0, 1, 0); // Placeholder y

    vector<int> entry_indices(m + 1);
    vector<int> return_patch_indices(m + 1);

    for (int i = 0; i <= m; ++i) {
        entry_indices[i] = current_idx();
        int V_i1 = 2 * i + 1;
        int V_i2 = 2 * i + 2;
        
        if (i == 0) {
            // Layer 0
            for (int w = 0; w < k_waste[0]; ++w) {
                int loop_push = current_idx();
                add_inst("POP", 1024, loop_push, 1000, loop_push + 1); 
                int loop_pop = current_idx();
                add_inst("POP", 1000, loop_pop + 1, 1000, loop_pop); 
            }
            
            int ret_inst = current_idx();
            add_inst("POP", V_i1, 0, 1, 0); 
            return_patch_indices[i] = ret_inst;
        } else {
            // Layer i > 0
            int V_prev1 = 2 * (i - 1) + 1;
            
            // Entry_i
            add_inst("POP", 1024, current_idx(), V_prev1, entry_indices[i-1]);
            
            // Return_{i-1} handler
            int ret_handler_idx = current_idx();
            program[return_patch_indices[i-1] - 1].x = ret_handler_idx;
            
            int transit_idx = ret_handler_idx + 1;
            int transit_len = 1 + 2 * k_waste[i] + 1;
            int check2_idx = transit_idx + transit_len;
            
            add_inst("POP", V_i1, transit_idx, 1024, check2_idx);
            
            // Transit
            add_inst("POP", 1024, current_idx(), V_i2, current_idx() + 1);
            
            for (int w = 0; w < k_waste[i]; ++w) {
                int loop_push = current_idx();
                add_inst("POP", 1024, loop_push, 1000, loop_push + 1);
                int loop_pop = current_idx();
                add_inst("POP", 1000, loop_pop + 1, 1000, loop_pop);
            }
            
            add_inst("POP", 1024, current_idx(), V_prev1, entry_indices[i-1]);
            
            // Check2
            add_inst("POP", 1024, current_idx() + 1, 1024, current_idx());
            
            int ret_inst = current_idx();
            add_inst("POP", V_i2, 0, 1, 0); 
            return_patch_indices[i] = ret_inst;
        }
    }
    
    program[0].y = entry_indices[m];
    program[return_patch_indices[m] - 1].x = 1;
    
    cout << program.size() << endl;
    for (const auto& ins : program) {
        if (ins.type == "HALT") {
            cout << "HALT PUSH " << ins.b << " GOTO " << ins.y << endl;
        } else {
            cout << "POP " << ins.a << " GOTO " << ins.x << " PUSH " << ins.b << " GOTO " << ins.y << endl;
        }
    }

    return 0;
}