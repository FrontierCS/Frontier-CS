#include <iostream>
#include <vector>
#include <cstdlib>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<int> parent(n + 1, 0);
    vector<vector<int>> children(n + 1);

    // Root the tree at vertex 1
    for (int v = 2; v <= n; ++v) {
        int u = 1;
        while (true) {
            bool moved = false;
            for (int c : children[u]) {
                cout << "? 2 " << u << ' ' << v << ' ' << c << endl;
                cout.flush();
                int ans;
                cin >> ans;
                if (ans == -1) exit(0);   // Protocol violation
                if (ans == 0) {           // v is in the subtree of c
                    u = c;
                    moved = true;
                    break;
                }
            }
            if (!moved) {                 // u is the parent of v
                children[u].push_back(v);
                parent[v] = u;
                break;
            }
        }
    }

    cout << "!" << endl;
    for (int v = 2; v <= n; ++v) {
        cout << parent[v] << ' ' << v << endl;
    }
    cout.flush();

    return 0;
}