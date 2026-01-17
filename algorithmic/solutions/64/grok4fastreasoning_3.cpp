#include <bits/stdc++.h>
using namespace std;

int main() {
    long long n, T;
    cin >> n >> T;
    vector<long long> a(n);
    for(auto &x : a) cin >> x;
    vector<pair<long long, int>> items(n);
    for(int i = 0; i < n; i++) {
        items[i] = {a[i], i};
    }
    sort(items.rbegin(), items.rend());
    long long curr = 0;
    vector<int> select(n, 0);
    for(auto &p : items) {
        long long val = p.first;
        int idx = p.second;
        long long new_curr = curr + val;
        if (abs(new_curr - T) < abs(curr - T)) {
            curr = new_curr;
            select[idx] = 1;
        }
    }
    for(int i = 0; i < n; i++) {
        cout << select[i];
    }
    cout << endl;
    return 0;
}