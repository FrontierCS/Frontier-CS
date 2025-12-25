#include <iostream>
#include <vector>
#include <bitset>
#include <algorithm>
#include <cassert>

using namespace std;

const int N = 1000;

// List of moduli k such that sum k = 1000, each k <= 51.
// This list is: all integers from 25 to 51 inclusive except 26.
// Number of moduli = 26, sum = 1000.
static const int moduli[] = {
    25, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39,
    40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51
};
const int num_moduli = sizeof(moduli) / sizeof(moduli[0]);

int main() {
    vector<bitset<N>> A;
    vector<bool> B;
    
    // Process each modulus k
    for (int idx = 0; idx < num_moduli; ++idx) {
        int k = moduli[idx];
        int m = 2 * k;
        
        // For each residue r mod k
        for (int r = 0; r < k; ++r) {
            // Build transition arrays a and b
            vector<int> a(m), b(m);
            for (int state = 0; state < m; ++state) {
                int pos = state / 2;
                int parity = state % 2;
                // Transition on input 0
                int new_pos = (pos + 1) % k;
                int new_parity = parity;
                a[state] = new_pos * 2 + new_parity;
                // Transition on input 1
                new_pos = (pos + 1) % k;
                new_parity = parity ^ (pos == r ? 1 : 0);
                b[state] = new_pos * 2 + new_parity;
            }
            
            // Output query
            cout << 1 << endl;
            cout << m;
            for (int i = 0; i < m; ++i) cout << " " << a[i];
            for (int i = 0; i < m; ++i) cout << " " << b[i];
            cout << endl;
            cout.flush();
            
            // Read response
            int x;
            cin >> x;
            if (cin.fail()) return 1;
            int parity = x % 2;
            
            // Build equation row: sum of S_i for i ≡ r (mod k) = parity (mod 2)
            bitset<N> row;
            for (int i = r; i < N; i += k) {
                row.set(i);
            }
            A.push_back(row);
            B.push_back(parity);
        }
    }
    
    // Now solve linear system A * S = B over GF(2)
    // Gaussian elimination on binary matrix
    const int n = N;
    vector<bitset<N>> mat = A; // copy
    vector<bool> rhs = B;
    vector<int> where(n, -1);
    
    int row = 0;
    for (int col = 0; col < n && row < mat.size(); ++col) {
        // find pivot
        int sel = -1;
        for (int i = row; i < mat.size(); ++i) {
            if (mat[i][col]) {
                sel = i;
                break;
            }
        }
        if (sel == -1) continue;
        // swap rows
        swap(mat[row], mat[sel]);
        swap(rhs[row], rhs[sel]);
        where[col] = row;
        // eliminate other rows
        for (int i = 0; i < mat.size(); ++i) {
            if (i != row && mat[i][col]) {
                mat[i] ^= mat[row];
                rhs[i] = rhs[i] ^ rhs[row];
            }
        }
        ++row;
    }
    
    // Back substitution (already done during elimination, but we extract solution)
    vector<int> S(n, 0);
    for (int i = 0; i < n; ++i) {
        if (where[i] != -1) {
            S[i] = rhs[where[i]];
        }
    }
    
    // Output guess
    cout << 0 << endl;
    for (int i = 0; i < n; ++i) {
        cout << S[i];
    }
    cout << endl;
    cout.flush();
    
    return 0;
}