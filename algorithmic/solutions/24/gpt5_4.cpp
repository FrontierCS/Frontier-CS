#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    while ( (cin >> n) ) {
        vector<string> C(n);
        for (int i = 0; i < n; ++i) {
            string s;
            cin >> s;
            if ((int)s.size() == n) {
                C[i] = s;
            } else {
                string row(1, s[0]);
                while ((int)row.size() < n) {
                    string t; cin >> t;
                    row.push_back(t[0]);
                }
                C[i] = row;
            }
        }
        
        deque<int> dq;
        dq.push_back(1);
        bool rev = false;
        auto getFront = [&](void)->int { return rev ? dq.back() : dq.front(); };
        auto getBack  = [&](void)->int { return rev ? dq.front() : dq.back(); };
        auto pushFront = [&](int v){ if (!rev) dq.push_front(v); else dq.push_back(v); };
        auto pushBack  = [&](int v){ if (!rev) dq.push_back(v); else dq.push_front(v); };
        
        for (int v = 2; v <= n; ++v) {
            int f = getFront();
            int b = getBack();
            char a = C[v-1][f-1];
            char bb = C[b-1][v-1];
            if (a == '0' && bb == '1') {
                rev = !rev;
                f = getFront();
                b = getBack();
                a = C[v-1][f-1];
                bb = C[b-1][v-1];
            }
            if (a == '1') pushFront(v);
            else pushBack(v); // bb must be '0'
        }
        
        vector<int> seq;
        if (!rev) {
            seq.assign(dq.begin(), dq.end());
        } else {
            seq.assign(dq.rbegin(), dq.rend());
        }
        
        auto rotateVec = [&](const vector<int>& a, int st)->vector<int> {
            int m = (int)a.size();
            vector<int> r(m);
            for (int i = 0; i < m; ++i) r[i] = a[(i + st) % m];
            return r;
        };
        auto lexLess = [&](const vector<int>& a, const vector<int>& b)->bool {
            for (int i = 0; i < (int)a.size(); ++i) {
                if (a[i] != b[i]) return a[i] < b[i];
            }
            return false;
        };
        auto consider = [&](vector<int>& best, const vector<int>& cand){
            if (lexLess(cand, best)) best = cand;
        };
        
        vector<char> ds(n-1);
        for (int i = 0; i < n-1; ++i) ds[i] = C[seq[i]-1][seq[i+1]-1];
        int changes = 0, idx = -1;
        for (int i = 0; i < n-2; ++i) if (ds[i] != ds[i+1]) { ++changes; idx = i; }
        
        vector<int> best = seq;
        if (n >= 2) {
            if (changes == 0) {
                // All edges along path are same color; any rotation (and reverse+rotation) works.
                best = rotateVec(seq, 0);
                for (int s = 1; s < n; ++s) consider(best, rotateVec(seq, s));
                vector<int> revseq = seq;
                reverse(revseq.begin(), revseq.end());
                for (int s = 0; s < n; ++s) consider(best, rotateVec(revseq, s));
            } else {
                // Exactly one change inside; only two valid rotations (start at either boundary).
                consider(best, rotateVec(seq, 0));
                consider(best, rotateVec(seq, idx + 1));
                vector<int> revseq = seq;
                reverse(revseq.begin(), revseq.end());
                vector<char> ds2(n-1);
                for (int i = 0; i < n-1; ++i) ds2[i] = C[revseq[i]-1][revseq[i+1]-1];
                int changes2 = 0, idx2 = -1;
                for (int i = 0; i < n-2; ++i) if (ds2[i] != ds2[i+1]) { ++changes2; idx2 = i; }
                if (changes2 == 0) {
                    for (int s = 0; s < n; ++s) consider(best, rotateVec(revseq, s));
                } else {
                    consider(best, rotateVec(revseq, 0));
                    consider(best, rotateVec(revseq, idx2 + 1));
                }
            }
        }
        
        for (int i = 0; i < n; ++i) {
            cout << best[i] << (i+1==n?'\n':' ');
        }
    }
    return 0;
}