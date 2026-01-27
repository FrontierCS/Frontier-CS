#include <bits/stdc++.h>
using namespace std;

int n;
unordered_map<long long, int> cacheS;

int getS(int l, int r) {
    if (l >= r) return 0;
    long long key = ((long long)l << 12) | r; // 12 bits enough for r up to 2000
    auto it = cacheS.find(key);
    if (it != cacheS.end()) return it->second;
    cout << "0 " << l << " " << r << endl;
    cout.flush();
    int ans = 0;
    if (!(cin >> ans)) exit(0);
    ans &= 1;
    cacheS[key] = ans;
    return ans;
}

int getX(int i, int j) {
    // returns [p_i > p_j] mod 2, for i < j
    return getS(i, j) ^ getS(i + 1, j) ^ getS(i, j - 1) ^ getS(i + 1, j - 1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    if (!(cin >> n)) return 0;

    vector<int> order; // indices sorted by increasing p-value
    order.reserve(n);

    for (int j = 1; j <= n; ++j) {
        if (order.empty()) {
            order.push_back(j);
            continue;
        }
        int low = 0, high = (int)order.size();
        while (low < high) {
            int mid = (low + high) >> 1;
            int i = order[mid];
            // less(j, i): true iff p_j < p_i, i.e., [p_i > p_j] == 1
            int x = (i < j) ? getX(i, j) : 0; // i is always < j in this algorithm
            if (x) high = mid;
            else low = mid + 1;
        }
        order.insert(order.begin() + low, j);
    }

    vector<int> p(n + 1, 0);
    for (int idx = 0; idx < n; ++idx) {
        p[order[idx]] = idx + 1;
    }

    cout << "1";
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << endl;
    cout.flush();

    return 0;
}