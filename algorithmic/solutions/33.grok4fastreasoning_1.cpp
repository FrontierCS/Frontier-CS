#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int q;
    cin >> q;
    vector<long long> ks(q);
    for (auto &k : ks) {
        cin >> k;
    }
    for (auto k : ks) {
        vector<bool> is_front;
        long long cur = k;
        while (cur > 2) {
            if (cur % 2 == 0) {
                is_front.push_back(false);
                cur /= 2;
            } else {
                is_front.push_back(true);
                cur--;
            }
        }
        int steps = is_front.size();
        int n = 1 + steps;
        reverse(is_front.begin(), is_front.end());
        deque<int> deq;
        deq.push_back(0);
        for (int v = 1; v < n; ++v) {
            if (is_front[v - 1]) {
                deq.push_front(v);
            } else {
                deq.push_back(v);
            }
        }
        cout << n << '\n';
        for (size_t i = 0; i < deq.size(); ++i) {
            if (i > 0) cout << ' ';
            cout << deq[i];
        }
        cout << '\n';
    }
    return 0;
}