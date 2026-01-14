#include <bits/stdc++.h>
using namespace std;

const int N = 1000;   // length of the hidden string
const int Q = 1000;   // number of queries we will make

// Perform a query with parameters p and r.
// The DFA has m = 2p states and computes the parity of bits at positions i with i mod p == r.
int query(int p, int r) {
    int m = 2 * p;
    vector<int> a(m), b_seq(m);
    for (int s = 0; s < m; ++s) {
        int c = s / 2;
        int parity = s % 2;
        int new_c = (c + 1) % p;
        // transition on reading '0'
        a[s] = new_c * 2 + parity;
        // transition on reading '1'
        int new_parity = parity ^ (c == r ? 1 : 0);
        b_seq[s] = new_c * 2 + new_parity;
    }
    cout << "1 " << m;
    for (int i = 0; i < m; ++i) cout << " " << a[i];
    for (int i = 0; i < m; ++i) cout << " " << b_seq[i];
    cout << endl;
    cout.flush();
    int x;
    cin >> x;
    return x;
}

int main() {
    int n;
    cin >> n;   // n is always 1000

    // basis of reduced vectors (left-hand sides) to test independence
    vector<bitset<N>> basis;
    // collected independent equations: (original vector, response bit)
    vector<pair<bitset<N>, int>> equations;

    // Generate candidate pairs (p, r) in increasing order of p,
    // and for each p take r = 0 .. p-2 (skipping r = p-1 to avoid trivial dependence).
    for (int p = 2; p <= 51; ++p) {
        for (int r = 0; r <= p - 2; ++r) {
            // Build the vector v that has 1 at positions i with i % p == r.
            bitset<N> v;
            for (int i = 0; i < N; ++i) {
                if (i % p == r) v.set(i);
            }
            // Reduce v by the current basis.
            bitset<N> vred = v;
            for (const auto& b : basis) {
                // find the pivot (first set bit) of b
                int pivot = -1;
                for (int i = 0; i < N; ++i) {
                    if (b[i]) {
                        pivot = i;
                        break;
                    }
                }
                if (pivot != -1 && vred[pivot]) {
                    vred ^= b;
                }
            }
            if (vred.none()) {
                continue;   // linearly dependent, skip this candidate
            }
            // Independent: make the query.
            int x = query(p, r);
            int resp = x % 2;   // the parity bit we need
            equations.push_back({v, resp});
            // Insert the reduced vector into the basis.
            basis.push_back(vred);
            if (equations.size() == N) break;
        }
        if (equations.size() == N) break;
    }

    // Build the augmented matrix for Gaussian elimination.
    // Each row is a bitset of length N+1: first N bits for the equation,
    // last bit for the response.
    vector<bitset<N + 1>> mat(N);
    for (int i = 0; i < N; ++i) {
        mat[i] = bitset<N + 1>();
        for (int j = 0; j < N; ++j) {
            if (equations[i].first[j]) mat[i].set(j);
        }
        if (equations[i].second) mat[i].set(N);
    }

    // Gaussian elimination over GF(2) to reduced row echelon form.
    int row = 0;
    for (int col = 0; col < N; ++col) {
        int pivot = -1;
        for (int r = row; r < N; ++r) {
            if (mat[r][col]) {
                pivot = r;
                break;
            }
        }
        if (pivot == -1) continue;
        swap(mat[row], mat[pivot]);
        for (int r = 0; r < N; ++r) {
            if (r != row && mat[r][col]) {
                mat[r] ^= mat[row];
            }
        }
        ++row;
        if (row == N) break;
    }

    // Extract the solution.
    string S(N, '0');
    for (int i = 0; i < N; ++i) {
        for (int col = 0; col < N; ++col) {
            if (mat[i][col]) {
                if (mat[i][N]) S[col] = '1';
                break;
            }
        }
    }

    cout << "0 " << S << endl;
    cout.flush();
    return 0;
}