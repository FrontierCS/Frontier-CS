#include <iostream>
#include <vector>
#include <functional>
#include <algorithm>
using namespace std;

int main() {
    int n, k;
    cin >> n >> k;
    
    vector<char> resp(n+1);
    vector<int> L; // indices with 'N' response
    
    // Initial reset and query all bakeries
    cout << "R" << endl;
    cout.flush();
    for (int i = 1; i <= n; ++i) {
        cout << "? " << i << endl;
        cout.flush();
        cin >> resp[i];
        if (resp[i] == 'N') {
            L.push_back(i);
        }
    }
    
    int d = L.size(); // initial estimate
    vector<int> parent(n+1);
    for (int i = 1; i <= n; ++i) parent[i] = i;
    
    function<int(int)> find = [&](int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    };
    
    auto unite = [&](int a, int b) {
        int ra = find(a), rb = find(b);
        if (ra != rb) {
            parent[rb] = ra;
        }
    };
    
    // Process each N bakery in order
    for (size_t idx = 0; idx < L.size(); ++idx) {
        int i = L[idx];
        int rep_i = find(i);
        int tested = 0;
        const int LIMIT = 30; // maximum number of equality tests per i
        
        // Look at previous N bakeries from right to left (most recent first)
        for (int jdx = idx-1; jdx >= 0; --jdx) {
            int j = L[jdx];
            if (i - j <= k) continue; // within window, cannot be equal (otherwise i would have been Y)
            
            int rep_j = find(j);
            if (rep_i == rep_j) continue; // already same group
            
            // Perform equality test with a reset
            cout << "R" << endl;
            cout.flush();
            cout << "? " << j << endl;
            cout.flush();
            char tmp; cin >> tmp; // read response for j (should be 'N')
            cout << "? " << i << endl;
            cout.flush();
            char ans; cin >> ans;
            
            tested++;
            if (ans == 'Y') {
                // Equal types: merge groups and decrease distinct count
                unite(i, j);
                d--;
                break;
            }
            
            if (tested >= LIMIT) break; // limit reached
        }
    }
    
    cout << "! " << d << endl;
    cout.flush();
    
    return 0;
}