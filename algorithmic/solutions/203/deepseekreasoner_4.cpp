#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& att) {
    cout << "Query " << att.size();
    for (int id : att) cout << " " << id;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    int N;
    cin >> N;
    int total = 2 * N;
    
    // Query all to get base number of distinct colors (should be N)
    vector<int> all(total);
    iota(all.begin(), all.end(), 1);
    int base = query(all);
    
    vector<pair<int, int>> pairs;
    // Assume chameleons 1..N are gender X, and N+1..2N are gender Y
    for (int x = 1; x <= N; ++x) {
        int lo = N + 1, hi = total;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            // Y_left = {lo, lo+1, ..., mid}
            vector<int> attend;
            for (int i = 1; i <= total; ++i) {
                if (i == x || (i >= lo && i <= mid)) continue;
                attend.push_back(i);
            }
            int res = query(attend);
            if (res < base) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        pairs.emplace_back(x, lo);
    }
    
    for (const auto& p : pairs) {
        cout << "Answer " << p.first << " " << p.second << endl;
    }
    
    return 0;
}