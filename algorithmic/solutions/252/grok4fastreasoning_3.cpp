#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n + 1, 0);
    auto find_successor = [&](int u) -> int {
        int low = 1, high = n;
        while (low < high) {
            int mid = (low + high) / 2;
            int size_s = mid - low + 1;
            cout << "? " << u << " 1 " << size_s;
            for (int i = low; i <= mid; ++i) {
                cout << " " << i;
            }
            cout << endl;
            int resp;
            cin >> resp;
            if (resp == 1) {
                high = mid;
            } else {
                low = mid + 1;
            }
        }
        return low;
    };
    for (int u = 1; u <= n; ++u) {
        a[u] = find_successor(u);
    }
    // Now compute R1
    set<int> r1;
    int cur = 1;
    set<int> seen;
    while (seen.find(cur) == seen.end()) {
        seen.insert(cur);
        cur = a[cur];
    }
    r1 = seen;
    // Now compute A
    vector<int> A;
    auto is_in_A = [&](int x) -> bool {
        unordered_set<int> visited;
        cur = x;
        while (visited.find(cur) == visited.end()) {
            visited.insert(cur);
            if (r1.find(cur) != r1.end()) {
                return true;
            }
            cur = a[cur];
        }
        return false;
    };
    for (int x = 1; x <= n; ++x) {
        if (is_in_A(x)) {
            A.push_back(x);
        }
    }
    // Output
    cout << "! " << A.size();
    for (int room : A) {
        cout << " " << room;
    }
    cout << endl;
    return 0;
}