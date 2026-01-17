#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    unsigned int k;
    std::cin >> k;

    if (k == 1) {
        std::cout << 1 << std::endl;
        std::cout << "HALT PUSH 1 GOTO 1" << std::endl;
        return 0;
    }

    unsigned int q = (k - 1) / 2;
    std::vector<int> bits;
    if (q == 0) {
        // This case would be for k=1, which is handled above.
        // For q=0, m should be 0, but to have a bit representation, 
        // we can consider it as a single 0 bit if needed.
        // However, the logic works for q > 0.
    }
    
    unsigned int temp_q = q;
    if (temp_q == 0) { // For k=3, q=1. For k=1, q=0.
        // A simple q=0 case might need one bit to represent it
        // but problem constraints k>=1 means q>=0.
        // if k=3, q=1, needs a bit. if k=1, q=0.
        // let's just make sure bits is never empty for q>0
        if (q>0) {
           while (temp_q > 0) {
                bits.push_back(temp_q % 2);
                temp_q /= 2;
           }
        }
    } else {
        while (temp_q > 0) {
            bits.push_back(temp_q % 2);
            temp_q /= 2;
        }
    }
    
    if (bits.empty() && q > 0) { // Should not happen for q>0
       // Failsafe for very large numbers
       int num_bits = floor(log2(q)) + 1;
       temp_q = q;
       for(int i = 0; i < num_bits; ++i) {
           bits.push_back(temp_q % 2);
           temp_q /= 2;
       }
    }


    std::reverse(bits.begin(), bits.end());
    
    if (q > 0 && bits.empty()) { // e.g. q=1
        bits.push_back(1);
    }
    
    int m = bits.size();
    if (q == 0) m = 0;


    int n = m + 3;
    std::cout << n << std::endl;

    // Instruction 1: Entry point, pushes the first token.
    std::cout << "POP 1 GOTO 2 PUSH 1 GOTO 2" << std::endl;

    // Instructions 2 to m+1: The chain for processing bits of q.
    for (int i = 0; i < m; ++i) {
        int instr_idx = i + 2;
        if (bits[i] == 1) {
            // For a '1' bit.
            std::cout << "HALT PUSH 1 GOTO " << instr_idx + 1 << std::endl;
        } else {
            // For a '0' bit.
            std::cout << "POP 1 GOTO " << m + 2 << " PUSH 2 GOTO " << instr_idx + 1 << std::endl;
        }
    }

    // Instruction m+2: The "return" mechanism.
    std::cout << "POP 1 GOTO 2 PUSH 2 GOTO " << m + 2 << std::endl;

    // Instruction m+3: The final halt point.
    std::cout << "HALT PUSH 99 GOTO " << m + 2 << std::endl;

    return 0;
}