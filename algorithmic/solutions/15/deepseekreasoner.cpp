#include <iostream>
#include <vector>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> p(n);
    for (int i = 0; i < n; i++) {
        cin >> p[i];
    }
    // We will try to sort by repeatedly applying op(1,1)
    vector<pair<int,int>> ops;
    // Check if sorted
    auto is_sorted = [&]() {
        for (int i = 0; i < n; i++) {
            if (p[i] != i+1) return false;
        }
        return true;
    };
    // Apply op(1,1) up to 4n times or until sorted
    for (int step = 0; step < 4*n && !is_sorted(); step++) {
        // Apply op(1,1)
        int x = 1, y = 1;
        if (x + y >= n) break; // should not happen for n>=3
        // Perform the operation on p
        vector<int> q;
        // suffix of length y
        for (int i = n-y; i < n; i++) q.push_back(p[i]);
        // middle
        for (int i = x; i < n-y; i++) q.push_back(p[i]);
        // prefix of length x
        for (int i = 0; i < x; i++) q.push_back(p[i]);
        p = q;
        ops.push_back({x, y});
    }
    cout << ops.size() << endl;
    for (auto& op : ops) {
        cout << op.first << " " << op.second << endl;
    }
    return 0;
}