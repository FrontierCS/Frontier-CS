#include <bits/stdc++.h>
using namespace std;

const int M = 30; // number of robots to use
const int N = 1000;

int main() {
    int R, H;
    cin >> R >> H;
    
    // Generate deterministic codes for each position
    vector<unsigned long long> codes(N);
    mt19937_64 rng(12345); // fixed seed
    for (int i = 0; i < N; i++) {
        codes[i] = rng() & ((1ULL << M) - 1);
    }
    
    // Send robots for each bit
    for (int bit = 0; bit < M; bit++) {
        vector<int> positions;
        for (int i = 0; i < N; i++) {
            if ((codes[i] >> bit) & 1) {
                positions.push_back(i+1); // 1-indexed
            }
        }
        cout << "? " << positions.size();
        for (int p : positions) {
            cout << " " << p;
        }
        cout << endl;
        cout.flush();
    }
    
    // Get results
    cout << "@" << endl;
    cout.flush();
    int L;
    cin >> L;
    vector<int> res(L);
    for (int i = 0; i < L; i++) {
        cin >> res[i];
    }
    
    // Combine results into a mask
    unsigned long long mask = 0;
    for (int bit = 0; bit < M; bit++) {
        if (res[bit] == 1) {
            mask |= (1ULL << bit);
        }
    }
    
    // Find the pair that matches the mask
    int a = -1, b = -1;
    for (int i = 0; i < N; i++) {
        for (int j = i; j < N; j++) {
            if ((codes[i] | codes[j]) == mask) {
                a = i+1;
                b = j+1;
                break;
            }
        }
        if (a != -1) break;
    }
    
    // Output answer
    cout << "! " << a << " " << b << endl;
    cout.flush();
    
    return 0;
}