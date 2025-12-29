#include <iostream>
#include <vector>
#include <cassert>
using namespace std;

const int M = 100000;
const int B = 317;
const int Q = M / B;           // = 315
const int n1 = Q * Q - 1;      // = 99224

void solve() {
    // First query: n1 words of length B
    cout << "? " << n1;
    for (int i = 0; i < n1; i++) {
        cout << " " << B;
    }
    cout << endl;
    
    int response1;
    cin >> response1;
    if (response1 == 0) {
        // W < B
        // Second query: M words of length 1
        cout << "? " << M;
        for (int i = 0; i < M; i++) {
            cout << " 1";
        }
        cout << endl;
        
        int lines;
        cin >> lines;
        // lines = ceil(M / W)  =>  W = ceil(M / lines)
        int W = (M + lines - 1) / lines;
        cout << "! " << W << endl;
    } else {
        int l1 = response1;
        // Determine q = floor(W / B)
        int q = (n1 + l1 - 1) / l1;   // ceil(n1 / l1)
        // Verify (optional safety check)
        if ((n1 + q - 1) / q != l1) {
            q++;   // should not happen with our chosen parameters
        }
        
        // Second query: B blocks, each two words: (q*B, i) for i=1..B
        int n2 = 2 * B;
        cout << "? " << n2;
        int base = q * B;
        for (int i = 1; i <= B; i++) {
            cout << " " << base << " " << i;
        }
        cout << endl;
        
        int l2;
        cin >> l2;
        int r = 2 * B - l2;
        int W = base + r;
        cout << "! " << W << endl;
    }
}

int main() {
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}