#include <bits/stdc++.h>
using namespace std;

int N;
string r_base;
int K;

vector<int> find_direct_adj(const vector<int>& cand, const string& rbase, int k) {
    if (cand.empty()) return {};
    if (cand.size() == 1) {
        int u = cand[0];
        string ts = rbase;
        ts[u] = '1';
        cout << "? " << ts.substr(1) << endl;
        cout.flush();
        int kp;
        cin >> kp;
        if (kp <= k) return {u};
        else return {};
    }
    // larger
    string ts = rbase;
    for (int u : cand) ts[u] = '1';
    cout << "? " << ts.substr(1) << endl;
    cout.flush();
    int k1;
    cin >> k1;
    string tts(N + 1, '0');
    for (int u : cand) tts[u] = '1';
    cout << "? " << tts.substr(1) << endl;
    cout.flush();
    int qq;
    cin >> qq;
    bool has_b = (k1 < k) || (k1 > k && qq < (k1 - k));
    bool no_b = false;
    if (k1 > k) {
        if (qq < (k1 - k + 1)) no_b = true;
    } else if (k1 == k) {
        if (qq == 0) no_b = true;
    }
    if (no_b) {
        return {};
    }
    // recurse both
    int mid = cand.size() / 2;
    vector<int> left(cand.begin(), cand.begin() + mid);
    vector<int> right(cand.begin() + mid, cand.end());
    auto ladj = find_direct_adj(left, rbase, k);
    auto radj = find_direct_adj(right, rbase, k);
    ladj.insert(ladj.end(), radj.begin(), radj.end());
    return ladj;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int TT;
    cin >> TT;
    for (int tt = 0; tt < TT; ++tt) {
        cin >> N;
        string r(N + 1, '0');
        r[1] = '1';
        vector<bool> in_r(N + 1, false);
        in_r[1] = true;
        int size_r = 1;
        while (true) {
            cout << "? " << r.substr(1) << endl;
            cout.flush();
            int kk;
            cin >> kk;
            K = kk;
            if (kk == 0) {
                cout << "! " << (size_r == N ? 1 : 0) << endl;
                cout.flush();
                break;
            }
            vector<int> outside;
            for (int i = 1; i <= N; ++i) {
                if (!in_r[i]) outside.push_back(i);
            }
            r_base = r;
            auto added = find_direct_adj(outside, r, kk);
            for (int u : added) {
                r[u] = '1';
                in_r[u] = true;
                ++size_r;
            }
        }
    }
    return 0;
}