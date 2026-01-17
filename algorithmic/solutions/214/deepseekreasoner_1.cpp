#include <iostream>
#include <vector>
#include <utility>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n);
    vector<int> pos(n + 1); // pos[value] = index (0-based)
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    vector<pair<int, int>> ops; // store operations (1-indexed)

    // choose x = 3, so we can reverse segments of length 2 or 4
    const int x = 3;

    // process values from n down to 2
    for (int val = n; val >= 2; --val) {
        int p = pos[val];               // current position of val (0-based)
        int target = val - 1;           // where val should end up (0-based)
        while (p < target) {
            int dist = target - p;
            if (dist >= 3) {
                // reverse a segment of length 4: [p, p+3]
                int l = p, r = p + 3;
                int v1 = a[l], v2 = a[l+1], v3 = a[l+2], v4 = a[r];
                // perform reversal
                a[l] = v4; a[l+1] = v3; a[l+2] = v2; a[r] = v1;
                // update positions of the four affected values
                pos[v1] = r;
                pos[v2] = l + 2;
                pos[v3] = l + 1;
                pos[v4] = l;
                ops.push_back({l + 1, r + 1}); // convert to 1-indexed
                p = l + 3; // val moved to r
            } else {
                // reverse a segment of length 2: [p, p+1]
                int l = p, r = p + 1;
                swap(a[l], a[r]);
                pos[a[l]] = l;
                pos[a[r]] = r;
                ops.push_back({l + 1, r + 1});
                p = l + 1; // val moved to r
            }
        }
    }

    // output
    cout << x << endl;
    cout << ops.size() << endl;
    for (auto& op : ops) {
        cout << op.first << " " << op.second << endl;
    }

    return 0;
}