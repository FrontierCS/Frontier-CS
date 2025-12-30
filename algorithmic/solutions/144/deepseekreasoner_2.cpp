#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    int n;
    cin >> n;
    
    // Query whole set to get global medians M1, M2
    cout << "0 " << n;
    for (int i = 1; i <= n; ++i) cout << " " << i;
    cout << endl;
    cout.flush();
    
    int M1, M2;
    cin >> M1 >> M2;
    if (M1 > M2) swap(M1, M2);   // ensure M1 < M2
    
    const int anchor = 1;   // fixed anchor index
    vector<pair<int, int>> res(n + 1);  // store results for i != anchor
    
    // Step: query all subsets missing {i, anchor} for i != anchor
    for (int i = 1; i <= n; ++i) {
        if (i == anchor) continue;
        vector<int> indices;
        for (int j = 1; j <= n; ++j)
            if (j != i && j != anchor)
                indices.push_back(j);
        int k = indices.size();
        cout << "0 " << k;
        for (int x : indices) cout << " " << x;
        cout << endl;
        cout.flush();
        
        int a, b;
        cin >> a >> b;
        if (a > b) swap(a, b);
        res[i] = {a, b};
    }
    
    // Check if anchor is a median (Type F appears)
    for (int i = 1; i <= n; ++i) {
        if (i == anchor) continue;
        if (res[i].first == M1 - 1 && res[i].second == M2 + 1) {
            // anchor and i are the two medians
            cout << "1 " << anchor << " " << i << endl;
            cout.flush();
            return 0;
        }
    }
    
    // Anchor is not a median
    int i0 = -1;   // will store the index of the median we can directly identify
    bool anchor_small = false;   // true if anchor < M1, false if anchor > M2
    
    // Look for Type B: (M1, M2+1)  -> anchor < M1, i0 = M2
    for (int i = 1; i <= n; ++i) {
        if (i == anchor) continue;
        if (res[i].first == M1 && res[i].second == M2 + 1) {
            i0 = i;
            anchor_small = true;
            break;
        }
    }
    
    if (i0 != -1) {
        // Case: anchor < M1, i0 = M2
        // Build S_A = indices giving (M2, M2+1) (these are indices with value ≤ M1)
        vector<int> S_A;
        for (int i = 1; i <= n; ++i) {
            if (i == anchor || i == i0) continue;
            if (res[i].first == M2 && res[i].second == M2 + 1)
                S_A.push_back(i);
        }
        // Search for M1 inside S_A
        for (int x : S_A) {
            vector<int> indices;
            for (int j = 1; j <= n; ++j)
                if (j != i0 && j != x)
                    indices.push_back(j);
            int k = indices.size();
            cout << "0 " << k;
            for (int j : indices) cout << " " << j;
            cout << endl;
            cout.flush();
            
            int a, b;
            cin >> a >> b;
            if (a > b) swap(a, b);
            if (a == M1 - 1 && b == M2 + 1) {
                // x is M1
                cout << "1 " << i0 << " " << x << endl;
                cout.flush();
                return 0;
            }
        }
    } else {
        // Look for Type C: (M1-1, M2)  -> anchor > M2, i0 = M1
        for (int i = 1; i <= n; ++i) {
            if (i == anchor) continue;
            if (res[i].first == M1 - 1 && res[i].second == M2) {
                i0 = i;
                break;
            }
        }
        // Now anchor > M2, i0 = M1
        // Build S_E = indices giving (M1-1, M1) (these are indices with value ≥ M2)
        vector<int> S_E;
        for (int i = 1; i <= n; ++i) {
            if (i == anchor || i == i0) continue;
            if (res[i].first == M1 - 1 && res[i].second == M1)
                S_E.push_back(i);
        }
        // Search for M2 inside S_E
        for (int x : S_E) {
            vector<int> indices;
            for (int j = 1; j <= n; ++j)
                if (j != i0 && j != x)
                    indices.push_back(j);
            int k = indices.size();
            cout << "0 " << k;
            for (int j : indices) cout << " " << j;
            cout << endl;
            cout.flush();
            
            int a, b;
            cin >> a >> b;
            if (a > b) swap(a, b);
            if (a == M1 - 1 && b == M2 + 1) {
                // x is M2
                cout << "1 " << i0 << " " << x << endl;
                cout.flush();
                return 0;
            }
        }
    }
    
    // Should never reach here
    return 0;
}