#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n+1);
    vector<int> pos(n+1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    // choose x
    int x;
    if (n <= 3) {
        x = 1;   // only length 2 is usable
    } else {
        x = 3;   // lengths 4 and 2
    }

    vector<pair<int, int>> ops;

    // sort from smallest to largest
    for (int v = 1; v <= n; v++) {
        int p = pos[v];
        while (p > v) {
            if (p - v >= 3) {
                // use a reversal of length 4 (x+1)
                int l = p - 3;
                int r = p;
                // reverse segment a[l..r] of length 4
                swap(a[l], a[r]);
                swap(a[l+1], a[r-1]);
                // update positions
                for (int i = l; i <= r; i++) {
                    pos[a[i]] = i;
                }
                ops.push_back({l, r});
                p = l; // v is now at l
            } else {
                // use a reversal of length 2 (x-1 for x=3, or x+1 for x=1)
                int l = p - 1;
                int r = p;
                swap(a[l], a[r]);
                pos[a[l]] = l;
                pos[a[r]] = r;
                ops.push_back({l, r});
                p = l;
            }
        }
    }

    // output
    cout << x << "\n";
    cout << ops.size() << "\n";
    for (auto& op : ops) {
        cout << op.first << " " << op.second << "\n";
    }

    return 0;
}