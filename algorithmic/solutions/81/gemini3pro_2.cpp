#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <bitset>

using namespace std;

// The length of the string is fixed at 1000
const int N = 1000;

// Basis for Gaussian elimination
// basis[i] will store a bitset where the lowest set bit is at index i
bitset<N> basis[N];
// rhs_val[i] stores the result (0 or 1) for the equation basis[i]
int rhs_val[N];
// has_pivot[i] is true if we have a basis vector for pivot i
bool has_pivot[N];
// ans[i] will store the determined bit S[i]
int ans[N];

void solve() {
    int n_in;
    // Read N, though it's fixed to 1000
    if (!(cin >> n_in)) return;

    // Initialize pivot array
    for(int i = 0; i < N; ++i) has_pivot[i] = false;

    // Random number generator
    mt19937 rng(5489);
    int eq_count = 0;

    // We need N linearly independent equations to solve for N bits
    while (eq_count < N) {
        // Choose a modulus M. 
        // We need 2*M <= 102 for full score, so M <= 51.
        // We use a range [40, 51] to generate variety.
        int M = 40 + (rng() % 12);
        
        // Generate a random mask of length M
        vector<int> mask(M);
        for (int i = 0; i < M; ++i) {
            mask[i] = rng() % 2;
        }

        // Create the equation vector corresponding to this mask
        // Coefficient for S[i] is 1 if mask[i % M] == 1, else 0
        bitset<N> vec;
        for (int i = 0; i < N; ++i) {
            if (mask[i % M]) {
                vec.set(i);
            }
        }

        // Check if this vector is linearly independent of the current basis
        bitset<N> temp = vec;
        int pivot = -1;
        
        // Eliminate bits using existing basis
        for (int i = 0; i < N; ++i) {
            if (temp.test(i)) {
                if (has_pivot[i]) {
                    temp ^= basis[i];
                } else {
                    pivot = i;
                    break;
                }
            }
        }

        // If pivot != -1, the vector is independent
        if (pivot != -1) {
            // Perform the query
            int m_states = 2 * M;
            
            // Output '1' to indicate a query
            cout << "1" << endl;
            
            // Construct transition tables
            // States 0..M-1 represent parity 0
            // States M..2M-1 represent parity 1
            vector<int> a(m_states), b(m_states);
            for (int s = 0; s < m_states; ++s) {
                int r = s % M;         // current position modulo M
                int p = s / M;         // current parity
                int next_r = (r + 1) % M;
                
                // If input is '0', parity never changes
                a[s] = next_r + p * M;
                
                // If input is '1', parity flips if mask[r] == 1
                int next_p = p ^ mask[r];
                b[s] = next_r + next_p * M;
            }
            
            // Output m, sequence a, sequence b
            cout << m_states;
            for (int x : a) cout << " " << x;
            for (int x : b) cout << " " << x;
            cout << endl;

            // Read the final state
            int final_state;
            cin >> final_state;
            
            // Determine result parity
            // If final_state >= M, parity is 1, else 0
            int parity = (final_state >= M ? 1 : 0);

            // Add the new equation to the basis
            // We need to reduce the original 'vec' again to update the RHS correctly
            // (temp from check phase didn't track RHS)
            int current_rhs = parity;
            temp = vec;
            for (int i = 0; i < N; ++i) {
                if (temp.test(i)) {
                    if (has_pivot[i]) {
                        temp ^= basis[i];
                        current_rhs ^= rhs_val[i];
                    } else {
                        // Insert new basis vector
                        basis[i] = temp;
                        rhs_val[i] = current_rhs;
                        has_pivot[i] = true;
                        eq_count++;
                        break;
                    }
                }
            }
        }
    }

    // Solve the system using back-substitution
    for (int i = N - 1; i >= 0; --i) {
        int val = rhs_val[i];
        for (int j = i + 1; j < N; ++j) {
            if (basis[i].test(j)) {
                val ^= ans[j];
            }
        }
        ans[i] = val;
    }

    // Output guess
    cout << "0" << endl;
    for (int i = 0; i < N; ++i) {
        cout << ans[i];
    }
    cout << endl;
}

int main() {
    solve();
    return 0;
}