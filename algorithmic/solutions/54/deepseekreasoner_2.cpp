#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n;
    cin >> n;
    
    vector<int> dA(n + 1, 0), dB(n + 1, 0);
    
    // Query distances from node 1 to all other nodes
    for (int i = 2; i <= n; ++i) {
        cout << "? 1 " << i << endl;
        cout.flush();
        cin >> dA[i];
    }
    
    // Find node B farthest from node 1
    int B = 1;
    for (int i = 2; i <= n; ++i) {
        if (dA[i] > dA[B]) {
            B = i;
        }
    }
    
    // Query distances from node B to all other nodes
    // Note: dist(B,1) is already known as dA[B]
    dB[1] = dA[B];
    for (int i