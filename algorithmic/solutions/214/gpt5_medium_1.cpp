#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n+1), pos(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }
    
    // Choose odd x close to n/2 such that x+1 <= n
    int x;
    if (n == 1) x = 1;
    else {
        x = (n + 1) / 2;
        if (x % 2 == 0) x++;
        while (x + 1 > n && x >= 1) x -= 2;
        if (x < 1) x = 1;
    }
    
    vector<pair<int,int>> ops;
    auto do_reverse = [&](int l, int r){
        ops.emplace_back(l, r);
        while (l < r) {
            int v1 = a[l], v2 = a[r];
            swap(a[l], a[r]);
            pos[v1] = r;
            pos[v2] = l;
            ++l; --r;
        }
    };
    
    auto attempt_move_specific = [&](int s, int t, int K)->bool{
        if (K <= 0 || K > n) return false;
        int need = K - 1;
        if (((s + t - need) & 1) != 0) return false;
        int l = (s + t - need) / 2;
        int r = l + K - 1;
        if (l < 1 || r > n) return false;
        if (!(l <= s && s <= r && l <= t && t <= r)) return false;
        do_reverse(l, r);
        return true;
    };
    
    auto attempt_move = [&](int s, int t)->bool{
        if (attempt_move_specific(s, t, x + 1)) return true;
        if (attempt_move_specific(s, t, x - 1)) return true;
        return false;
    };
    
    for (int val = 1; val <= n; ++val) {
        int t = val;
        int s = pos[val];
        if (s == t) continue;
        int dist = abs(s - t);
        int xpar = x & 1;
        // Case 1: one-step if possible
        if (dist <= x && (((s + t) & 1) == xpar)) {
            attempt_move(s, t);
            continue;
        }
        // Same parity positions -> 2 steps
        if (((s ^ t) & 1) == 0) {
            int p1;
            if (dist > x) {
                p1 = (s < t ? t - x : t + x);
            } else {
                p1 = (s < t ? t - 1 : t + 1);
            }
            attempt_move(s, p1);
            s = pos[val];
            attempt_move(s, t);
        } else {
            // Different parity
            if (dist <= x) {
                attempt_move(s, t);
            } else {
                int p1 = (s < t ? s + x : s - x);
                attempt_move(s, p1);
                int s2 = pos[val];
                int p2 = (s < t ? t - x : t + x);
                attempt_move(s2, p2);
                int s3 = pos[val];
                attempt_move(s3, t);
            }
        }
    }
    
    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}