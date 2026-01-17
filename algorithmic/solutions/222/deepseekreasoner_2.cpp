#include <iostream>
#include <vector>
#include <unordered_map>
#include <cstdlib>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    const int m = 500; // baby step size

    for (int graph = 0; graph < n; ++graph) {
        // get a vertex on the cycle
        int a;
        cout << "? 1 1" << endl;
        cin >> a;

        vector<int> baby(m);
        unordered_map<int, int> baby_index;
        baby[0] = a;
        baby_index[a] = 0;

        int cur = a;
        int L = -1;
        // walk m-1 steps
        for (int i = 1; i < m; ++i) {
            cout << "? " << cur << " 1" << endl;
            int nxt;
            cin >> nxt;
            if (nxt == a) {
                L = i; // cycle length
                break;
            }
            baby[i] = nxt;
            baby_index[nxt] = i;
            cur = nxt;
        }

        if (L == -1) {
            // L > m, perform giant steps
            for (int j = 1; ; ++j) {
                long long x = 1LL * j * m;
                cout << "? " << a << " " << x << endl;
                int v;
                cin >> v;
                if (baby_index.find(v) != baby_index.end()) {
                    int i = baby_index[v];
                    L = x - i;
                    break;
                }
            }
        }

        cout << "! " << L << endl;
        int resp;
        cin >> resp;
        if (resp == -1) {
            exit(0);
        }
        // if resp == 1, continue to next graph
    }

    return 0;
}