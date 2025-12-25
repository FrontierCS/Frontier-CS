#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>

struct Instruction {
    std::string type;
    int a, x, b, y;
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    unsigned int k_unsigned;
    std::cin >> k_unsigned;
    long long k = k_unsigned;

    if (k == 1) {
        std::cout << 1 << std::endl;
        std::cout << "HALT PUSH 1 GOTO 1" << std::endl;
        return 0;
    }

    long long h = (k - 1) / 2;
    int L = (h == 0) ? -1 : static_cast<int>(floor(log2(h)));

    std::vector<Instruction> prog;

    // PC 1: Entry point
    prog.push_back({"POP", 999, 0, 1000, 0}); 

    // --- Pusher logic for h items ---
    // This part takes h steps.
    // Based on binary representation of h = (b_L ... b_0)_2
    // We process bits from L down to 0.
    // Tokens:
    // S_i: "Start bit i" - value i+1
    // D_i: "Double for bit i" - value i+1+32
    // A_i: "Add for bit i" - value i+1+64
    
    // PC 2 to 3L+4: pusher machine
    for (int i = L; i >= 0; --i) {
        int S_i = i + 1;
        int D_i = i + 1 + 32;
        int A_i = i + 1 + 64;

        int next_S = (i > 0) ? i : prog.size() + 3 * (L + 1) + 2; // After last bit, jump to popper

        // S_i logic
        prog.push_back({"POP", D_i, 3 * (L - i) + 4, A_i, next_S});
        // A_i logic
        prog.push_back({"POP", S_i, 3 * (L - i) + 2, D_i, 3 * (L - i) + 2});
        // D_i logic
        prog.push_back({"POP", S_i, 3 * (L - i) + 3, S_i, 3 * (L - i) + 4});
    }

    // Set initial jump from PC 1
    prog[0].y = 2; // Start with S_L
    // Modify S_L to reflect b_L
    if ((h >> L) & 1) { // if b_L = 1, start with Add
        prog[1].b = L + 1 + 64; // A_L
    } else { // if b_L = 0, start with Double
        prog[1].b = L + 1 + 32; // D_L
    }
    prog[1].x = 3 * (L - L) + 2; // This is S_L's own address
    prog[1].y = 3 * (L - L) + 2;
    
    // Wire the chain for h's binary expansion
    for (int i = L; i > 0; --i) {
        if ((h >> (i - 1)) & 1) { // if next bit is 1, PUSH A_{i-1}
            prog[3 * (L - i) + 2].y = 3 * (L - (i - 1)) + 3;
        } else { // if next bit is 0, PUSH D_{i-1}
            prog[3 * (L - i) + 2].y = 3 * (L - (i - 1)) + 4;
        }
    }
    
    // --- Popper logic ---
    // This part takes h steps.
    int popper_pc = prog.size() + 1;
    for (int i = 0; i <= L; ++i) {
        prog.push_back({"POP", i + 1, popper_pc, 0, popper_pc});
        prog.push_back({"POP", i + 1 + 32, popper_pc, 0, popper_pc});
        prog.push_back({"POP", i + 1 + 64, popper_pc, 0, popper_pc});
    }
    prog.push_back({"POP", 1000, prog.size() + 2, 0, popper_pc});

    // Final HALT instruction
    prog.push_back({"HALT", 0, 0, 999, 999});

    std::cout << prog.size() << std::endl;
    for (const auto& p : prog) {
        if (p.type == "HALT") {
            std::cout << "HALT PUSH " << p.b << " GOTO " << p.y << std::endl;
        } else {
            std::cout << "POP " << p.a << " GOTO " << p.x << " PUSH " << p.b << " GOTO " << p.y << std::endl;
        }
    }

    return 0;
}