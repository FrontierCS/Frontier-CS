#include <iostream>
#include <vector>
#include <bitset>
#include <random>
#include <cassert>
#include <algorithm>

using namespace std;

const int R = 75;
const int N = 1000;

int main() {
    // Generate random matrix M[R][N]
    // Store columns as bitset<R> for fast OR operations
    vector<bitset<R>> cols(N);
    // Store rows for constructing queries
    vector<vector<int>> queries(R);
    
    // Deterministic random number generator
    mt19937 rng(123456789);
    uniform_int_distribution<int> binary(0, 1);
    
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < N; ++j) {
            if (binary(rng)) {
                cols[j][i] = 1;
                queries[i].push_back(j);
            }
        }
    }
    
    // Send all robots
    for (int i = 0; i < R; ++i) {
        cout << "? " << queries[i].size();
        for (int pos : queries[i]) {
            cout << " " << pos + 1;   // positions are 1-based
        }
        cout << endl;
        cout.flush();
    }
    
    // Request results after one hour
    cout << "@" << endl;
    cout.flush();
    
    int L;
    cin >> L;
    assert(L == R);
    vector<int> ans(R);
    for (int i = 0; i < R; ++i) {
        cin >> ans[i];
    }
    
    // Build target bitset from answers
    bitset<R> target;
    for (int i = 0; i < R; ++i) {
        if (ans[i]) target.set(i);
    }
    
    // Brute-force search for the pair of columns whose OR matches target
    for (int i = 0; i < N; ++i) {
        for (int j = i; j < N; ++j) {
            bitset<R> OR = cols[i] | cols[j];
            if (OR == target) {
                cout << "! " << i + 1 << " " << j + 1 << endl;
                cout.flush();
                return 0;
            }
        }
    }
    
    // Fallback (should never be reached with a 2-separable matrix)
    cout << "! 1 1" << endl;
    cout.flush();
    return 0;
}