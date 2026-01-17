#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

int main() {
    int n;
    cin >> n;
    
    vector<int> parent(n + 1, 0);
    vector<vector<int>> children(n + 1);
    
    for (int x = 2; x <= n; ++x) {
        int u = 1;
        while (true) {
            bool found = false;
            for (int v : children[u]) {
                cout << "? 2 " << u << " " << x << " " << v << endl;
                cout.flush();
                int ans;
                cin >> ans;
                if (ans == -1) {
                    exit(0);
                }
                if (ans == 0) {
                    u = v;
                    found = true;
                    break;
                }
            }
            if (!found) {
                parent[x] = u;
                children[u].push_back(x);
                break;
            }
        }
    }
    
    cout << "!" << endl;
    for (int i = 2; i <= n; ++i) {
        cout << parent[i] << " " << i << endl;
    }
    cout.flush();
    
    return 0;
}