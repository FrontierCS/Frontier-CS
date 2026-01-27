#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int u = 1; u <= n; ++u) {
        int low = 1, high = n;
        while (low < high) {
            int mid = low + (high - low) / 2;
            cout << "? " << u << " 1 " << mid;
            for (int j = 1; j <= mid; ++j) {
                cout << " " << j;
            }
            cout << endl;
            cout.flush();
            int res;
            cin >> res;
            if (res == 1) {
                high = mid;
            } else {
                low = mid + 1;
            }
        }
        a[u] = low;
    }
    // Find cycle of 1
    vector<int> path;
    unordered_set<int> seen;
    int cur = 1;
    while (seen.count(cur) == 0) {
        seen.insert(cur);
        path.push_back(cur);
        cur = a[cur];
    }
    // Find cycle start index
    size_t cycle_start = 0;
    for (size_t i = 0; i < path.size(); ++i) {
        if (path[i] == cur) {
            cycle_start = i;
            break;
        }
    }
    set<int> cycle_set;
    for (size_t i = cycle_start; i < path.size(); ++i) {
        cycle_set.insert(path[i]);
    }
    // Find A
    vector<int> A;
    for (int x = 1; x <= n; ++x) {
        int pos = x;
        for (int i = 0; i < n; ++i) {
            pos = a[pos];
        }
        if (cycle_set.count(pos)) {
            A.push_back(x);
        }
    }
    // Output
    cout << "! " << A.size();
    for (int room : A) {
        cout << " " << room;
    }
    cout << endl;
    cout.flush();
    return 0;
}