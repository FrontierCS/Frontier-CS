#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

using namespace std;

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
    vector<int> bits;
    if (m > 0) {
        unsigned int temp_m = m;
        while (temp_m > 0) {
            bits.push_back(temp_m % 2);
            temp_m /= 2;
        }
        reverse(bits.begin(), bits.end());
    } else { // This case is for k=3, where m=1
        bits.push_back(1);
    }

    int L = bits.size();
    int num_zeros = 0;
    for (int bit : bits) {
        if (bit == 0) {
            num_zeros++;
        }
    }

    int n = L + num_zeros + 2;
    cout << n << endl;

    map<int, int> zero_bit_indices;
    int current_b_idx = L + 3;
    for (int i = 0; i < L; ++i) {
        if (bits[i] == 0) {
            zero_bit_indices[i] = current_b_idx++;
        }
    }

    // Instruction 1: Entry
    cout << "POP 1 GOTO 2 PUSH 1 GOTO 2" << endl;
    // Instruction 2: Halt
    cout << "HALT PUSH 1 GOTO 3" << endl;

    // A_i instructions
    for (int i = 0; i < L; ++i) {
        int bit = bits[i];
        int A_idx = i + 3;
        int next_A_idx = (i == L - 1) ? 2 : A_idx + 1;
        
        if (bit == 1) {
            cout << "POP 1 GOTO " << next_A_idx << " PUSH 1 GOTO " << next_A_idx << endl;
        } else {
            int B_idx = zero_bit_indices[i];
            cout << "POP 1 GOTO " << B_idx << " PUSH 2 GOTO " << B_idx << endl;
        }
    }

    // B_i instructions
    for (int i = 0; i < L; ++i) {
        if (bits[i] == 0) {
            int B_idx = zero_bit_indices[i];
            cout << "POP 1 GOTO 2 PUSH 2 GOTO " << B_idx << endl;
        }
    }

    return 0;
}