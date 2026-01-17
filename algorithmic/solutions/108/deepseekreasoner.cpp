#include <iostream>
#include <vector>
using namespace std;

int n, m, N;
int curU;

int query(int x, int d) {
    cout << "? " << x << " " << d << endl;
    int res;
    cin >> res;
    curU = res;
    return res;
}

int main() {
    cin >> n >> m;
    N = n * m;
    
    // Step 1: Scan ring 0 to find max U position
    int maxU = -1, maxIndex = -1;
    for (int i = 1; i <= N; i++) {
        query(0, 1);
        if (curU > maxU) {
            maxU = curU;
            maxIndex = i;
        }
    }
    if (maxIndex == -1) maxIndex = 0;
    
    // Rotate ring 0 to the position that gave max U
    for (int i = 0; i < maxIndex; i++) {
        query(0, 1);
    }
    
    const int MAX_STEPS = 200;
    
    // Step 2: Align each other ring with ring 0
    for (int i = 1; i < n; i++) {
        int u0 = curU;
        int u1 = query(i, 1); // rotate clockwise once
        int dir;
        if (u1 > u0) dir = 1;
        else if (u1 < u0) dir = -1;
        else dir = 1; // arbitrary choice
        
        int steps = 0;
        int prevU = u1;
        while (steps < MAX_STEPS) {
            int newU = query(i, dir);
            steps++;
            if (newU < prevU) {
                // passed the peak, go back
                query(i, -dir);
                break;
            }
            prevU = newU;
        }
    }
    
    // After aligning all rings, relative positions are zero
    cout << "!";
    for (int i = 1; i < n; i++) {
        cout << " 0";
    }
    cout << endl;
    
    return 0;
}