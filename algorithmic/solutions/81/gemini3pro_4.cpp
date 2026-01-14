#include <iostream>
#include <vector>
#include <bitset>
#include <algorithm>

using namespace std;

// Structure to store query details
struct Query {
    int P, R;
    bitset<1000> mask;
};

int N;
vector<Query> queries;
// Basis for checking linear independence
// basis[i] stores a vector whose lowest set bit is i
bitset<1000> basis[1000];
bool has_basis[1000];

// Tries to add a query with period P and remainder R to the set
void add_query(int P, int R) {
    if (queries.size() == N) return;
    
    bitset<1000> mask;
    for (int i = 0; i < N; ++i) {
        if (i % P == R) mask.set(i);
    }
    
    bitset<1000> temp = mask;
    // Gaussian elimination step to check independence against current basis
    for (int i = 0; i < N; ++i) {
        if (temp.test(i)) {
            if (!has_basis[i]) {
                // Found a pivot, so this vector is independent
                has_basis[i] = true;
                basis[i] = temp;
                queries.push_back({P, R, mask});
                return;
            }
            temp ^= basis[i];
        }
    }
}

int main() {
    // Optimize IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    // We need 1000 independent queries to determine 1000 bits.
    // We construct queries based on modular arithmetic: sum of S[i] where i % P == R.
    // To maximize score, we want m = 2*P <= 102, so P <= 51.
    // We prioritize small P. If we cannot find 1000 independent queries with P <= 51,
    // we continue with larger P.
    
    for (int P = 1; P <= 501; ++P) {
        if (queries.size() == N) break;
        for (int R = 0; R < P; ++R) {
            add_query(P, R);
            if (queries.size() == N) break;
        }
    }

    // Execute the selected queries
    vector<int> results(N);
    for (int i = 0; i < N; ++i) {
        int P = queries[i].P;
        int R = queries[i].R;
        int m = 2 * P;
        
        // Output query command
        cout << "1 " << m;
        
        vector<int> a(m), b(m);
        // Construct DFA
        // State encoded as 2*s + p, where s is position mod P, p is parity
        for (int u = 0; u < m; ++u) {
            int s = u / 2;
            int p = u % 2;
            
            int next_s = (s + 1) % P;
            
            // If input is '0', parity does not change
            a[u] = 2 * next_s + p;
            
            // If input is '1', parity flips if current position matches R
            // Position matches R if s == R
            b[u] = 2 * next_s + (p ^ (s == R ? 1 : 0));
        }
        
        cout << " ";
        for (int j = 0; j < m; ++j) cout << a[j] << (j == m - 1 ? "" : " ");
        cout << " ";
        for (int j = 0; j < m; ++j) cout << b[j] << (j == m - 1 ? "" : " ");
        cout << endl; // Flush output
        
        int res;
        cin >> res;
        // The result's parity bit gives the XOR sum
        results[i] = res % 2;
    }
    
    // Solve the linear system Matrix * S = Results using Gauss-Jordan elimination
    // Matrix[i] corresponds to the mask of the i-th query
    vector<bitset<1000>> matrix(N);
    for(int i = 0; i < N; ++i) matrix[i] = queries[i].mask;
    
    for (int col = 0; col < N; ++col) {
        int pivot = -1;
        for (int row = col; row < N; ++row) {
            if (matrix[row].test(col)) {
                pivot = row;
                break;
            }
        }
        
        if (pivot == -1) continue; // Should not happen with N independent vectors
        
        swap(matrix[col], matrix[pivot]);
        swap(results[col], results[pivot]);
        
        for (int row = 0; row < N; ++row) {
            if (row != col && matrix[row].test(col)) {
                matrix[row] ^= matrix[col];
                results[row] ^= results[col];
            }
        }
    }
    
    // Output guess
    cout << "0 ";
    for (int i = 0; i < N; ++i) cout << results[i];
    cout << endl;

    return 0;
}