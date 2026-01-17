#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    long long k;
    cin >> k;

    if (k == 1) {
        cout << 1 << endl;
        cout << "HALT PUSH 1 GOTO 1" << endl;
        return 0;
    }

    long long m = (k - 1) / 2;
    vector<int> bits;
    if (m == 0) {
        // For k=3, m=1. For k>1 odd, m>=1. This case is not strictly necessary.
        bits.push_back(0); 
    } else {
        long long temp_m = m;
        while (temp_m > 0) {
            bits.push_back(temp_m % 2);
            temp_m /= 2;
        }
    }

    int L = bits.size();
    int n = 2 * L + 3;

    cout << n << endl;

    // Instruction 1: Entry point for k. Jumps to the start of P(m).
    // The start of P(m) corresponds to the most significant bit of m, which is at index L-1.
    int p_m_entry = 2 * (L - 1) + 3;
    cout << "PUSH 1 GOTO " << p_m_entry << endl;

    // Instruction 2: Final halt instruction.
    cout << "HALT PUSH 1 GOTO 2" << endl;

    // Instructions for P(m), based on bits of m from LSB to MSB.
    for (int i = 0; i < L; ++i) {
        int bit = bits[i];
        int c_i = 2 * i + 3;
        int r_i = 2 * i + 4;

        // C_i instruction
        cout << "POP 1 GOTO " << r_i << " PUSH 2 GOTO " << r_i << endl;

        // R_i instruction
        int next_instr;
        if (i > 0) {
            // Jump to the C block of the next less significant bit
            next_instr = 2 * (i - 1) + 3;
        } else {
            // Base case: jump back to instruction 1, which will try to POP.
            // If the initial marker is there, it proceeds to HALT.
            next_instr = 1;
        }

        if (bit == 0) {
            cout << "POP 1 GOTO " << next_instr << " PUSH 2 GOTO " << next_instr << endl;
        } else { // bit == 1
            cout << "POP 2 GOTO " << next_instr << " PUSH 1 GOTO " << next_instr << endl;
        }
    }

    return 0;
}