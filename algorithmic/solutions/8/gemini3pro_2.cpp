#include <iostream>
#include <vector>
#include <string>

using namespace std;

typedef long long ll;

struct Instruction {
    string type;
    int a; // or b for halt/push
    int x; // or y for halt/push
    int b;
    int y;
};

vector<Instruction> program;

// Helper to add instruction to the list
void add_inst(string type, int a, int x, int b = 0, int y = 0) {
    Instruction inst;
    inst.type = type;
    inst.a = a;
    inst.x = x;
    inst.b = b;
    inst.y = y;
    program.push_back(inst);
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ll k;
    if (!(cin >> k)) return 0;

    // For small k, use a simple linear chain construction.
    // The overhead of the complex loop solution is around 120 steps.
    if (k < 300) {
        if (k == 1) {
            cout << "1\nHALT PUSH 1 GOTO 1" << endl;
            return 0;
        }
        
        // Strategy for K:
        // 1. Push 1 (1 step)
        // 2. Loop (K-3)/2 times: Push 2, Pop 2 (2 steps each)
        // 3. Pop 1 (1 step)
        // 4. Halt (1 step)
        // Total steps = 1 + (K-3) + 1 + 1 = K.
        
        // Inst 1: Push 1
        // Since stack is initially empty, POP fails and PUSH 1 GOTO 2 executes.
        add_inst("POP", 1000, 2, 1, 2); 
        
        ll pairs = (k - 3) / 2;
        int next_addr = 2;
        for (int i = 0; i < pairs; ++i) {
            // Push 2: Top is 1, so POP 1000 fails -> Pushes 2
            add_inst("POP", 1000, next_addr + 1, 2, next_addr + 1);
            // Pop 2: Top is 2, so POP 2 succeeds -> Pops 2
            add_inst("POP", 2, next_addr + 2, 1, next_addr + 2); 
            next_addr += 2;
        }
        
        // Pop 1
        add_inst("POP", 1, next_addr + 1, 1, next_addr + 1);
        
        // Halt: Stack empty -> Halts.
        add_inst("HALT", 1, next_addr + 1, 0, 0); 
        
        cout << program.size() << endl;
        for (const auto& inst : program) {
            if (inst.type == "HALT") {
                cout << "HALT PUSH " << inst.a << " GOTO " << inst.x << endl;
            } else {
                cout << "POP " << inst.a << " GOTO " << inst.x << " PUSH " << inst.b << " GOTO " << inst.y << endl;
            }
        }
        return 0;
    }

    // For large K, use a loop-based solution simulating a counter.
    // We define a cost function G(v) representing steps to clear value v from stack.
    // G(v) ~= 2 * G(v-1), providing exponential growth.
    // M=30 gives G(30) > 2^31.
    int M = 30;
    vector<ll> G(M + 1);
    // Base cost for v=1: Dispatch Loop checks M..1. Check 1 succeeds.
    // Cost = (Checks M..2 failing) + (Check 1 success).
    // Failing check costs 2 steps. Success costs 1 step.
    // G(1) = 2*(M-1) + 1 = 2M - 1.
    G[1] = 2LL * M - 1;
    for (int v = 2; v <= M; ++v) {
        // G(v) = Dispatch(v) + Expansion + 2*G(v-1)
        // Dispatch(v): 2*(M-v) + 1
        // Expansion: Push v-1, Push v-1 => 2 steps
        // Total overhead for v > 1: 2M - 2v + 3
        G[v] = (2LL * M - 2LL * v + 3) + 2LL * G[v - 1];
    }
    
    // Total steps = BurnSteps + LoadSteps + Sum(G(u)) + LoopEmptyCheck + Halt
    // LoopEmptyCheck: Checks M..1 on empty stack, all fail => 2M steps.
    // Halt => 1 step.
    // Fixed overhead = 2M + 1.
    
    ll target = k - (2LL * M + 1);
    vector<int> u;
    
    // Greedy decomposition of Target
    while (true) {
        int best_v = -1;
        // Each load adds 1 step plus G[v] steps
        for (int v = M; v >= 1; --v) {
            if (G[v] + 1 <= target) {
                best_v = v;
                break;
            }
        }
        if (best_v == -1) break;
        
        u.push_back(best_v);
        target -= (G[best_v] + 1);
    }
    
    // Remaining target must be satisfied by "Burn" instructions.
    // Burn adds pairs of steps (Push X, Pop X).
    // Target parity check: K is odd, 2M+1 is odd => Initial target even.
    // G[v] is odd => G[v]+1 is even.
    // Subtracting even from even => target remains even.
    // So target is always non-negative even number here.
    ll burn_pairs = target / 2;
    
    // Code Generation
    
    // 1. Burn Instructions
    int current_line = 1;
    for (int i = 0; i < burn_pairs; ++i) {
        // Pair: Push 1000, Pop 1000.
        // Line A: POP 1000 (fails) -> Push 1000 -> Goto B
        // Line B: POP 1000 (succeeds) -> Goto Next
        add_inst("POP", 1000, current_line + 1, 1000, current_line + 1);
        add_inst("POP", 1000, current_line + 2, 1, current_line + 2);
        current_line += 2;
    }
    
    // 2. Load Instructions
    int load_count = u.size();
    int loop_start = current_line + load_count;
    
    for (int i = 0; i < load_count; ++i) {
        int val = u[i];
        int next_addr = (i == load_count - 1) ? loop_start : current_line + 1;
        // PUSH val: POP 1000 (fails) -> Push val -> Goto Next
        add_inst("POP", 1000, next_addr, val, next_addr);
        current_line++;
    }
    
    // 3. Loop Instructions
    // Address mapping
    struct BlockAddr {
        int check;
        int fail;
        int expand;
        int p2;
    };
    vector<BlockAddr> blocks(M + 1);
    int addr = loop_start;
    
    // Check_30 is the entry point
    blocks[M].check = addr;
    
    for (int v = M; v >= 2; --v) {
        blocks[v].check = addr;
        blocks[v].fail = addr + 1;
        blocks[v].expand = addr + 2;
        blocks[v].p2 = addr + 3;
        addr += 4;
    }
    
    blocks[1].check = addr;
    blocks[1].fail = addr + 1;
    addr += 2;
    
    int halt_addr = addr;
    
    // Generate loop code
    for (int v = M; v >= 2; --v) {
        // Check_v: If Top==v -> Expand_v; Else -> Fail_v (Push v)
        add_inst("POP", v, blocks[v].expand, v, blocks[v].fail);
        
        // Fail_v: Pop v (restore) -> Check_{v-1}
        int next_check = blocks[v-1].check;
        add_inst("POP", v, next_check, 1, next_check);
        
        // Expand_v: Push v-1 -> P2_v
        add_inst("POP", 1000, blocks[v].p2, v - 1, blocks[v].p2);
        
        // P2_v: Push v-1 -> Check_M (Loop start)
        add_inst("POP", 1000, blocks[M].check, v - 1, blocks[M].check);
    }
    
    // v = 1
    // Check_1: If Top==1 -> Loop start; Else -> Fail_1 (Push 1)
    add_inst("POP", 1, blocks[M].check, 1, blocks[1].fail);
    
    // Fail_1: Pop 1 -> Halt
    add_inst("POP", 1, halt_addr, 1, halt_addr);
    
    // Halt
    add_inst("HALT", 999, halt_addr, 0, 0);
    
    // Output
    cout << program.size() << endl;
    for (const auto& inst : program) {
        if (inst.type == "HALT") {
            cout << "HALT PUSH " << inst.a << " GOTO " << inst.x << endl;
        } else {
            cout << "POP " << inst.a << " GOTO " << inst.x << " PUSH " << inst.b << " GOTO " << inst.y << endl;
        }
    }

    return 0;
}