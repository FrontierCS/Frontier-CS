#include <bits/stdc++.h>
using namespace std;

static int n;
static vector<char> inS;
static int qcnt;

static int askString(const string &s) {
    cout << "? " << s << '\n' << flush;
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    ++qcnt;
    return ans;
}

static int askMask(const vector<char> &mask) {
    string s(n, '0');
    for (int i = 0; i < n; i++) if (mask[i]) s[i] = '1';
    return askString(s);
}

static int askRange(const vector<int> &cand, int l, int r, bool withS) {
    string s(n, '0');
    if (withS) {
        for (int i = 0; i < n; i++) if (inS[i]) s[i] = '1';
    }
    for (int i = l; i < r; i++) s[cand[i]] = '1';
    return askString(s);
}

static int findVertexToAdd(const vector<int> &cand, int fS) {
    int l = 0, r = (int)cand.size();
    while (r - l > 1) {
        int m = (l + r) / 2;
        int fA = askRange(cand, l, m, false);
        int fSA = askRange(cand, l, m, true);
        if (fSA < fS + fA) r = m;
        else l = m;
    }
    return cand[l];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        cin >> n;
        inS.assign(n, 0);
        qcnt = 0;

        int sz = 1;
        inS[0] = 1;

        while (true) {
            int fS = askMask(inS);
            if (fS == 0) {
                cout << "! " << (sz == n ? 1 : 0) << '\n' << flush;
                break;
            }

            vector<int> cand;
            cand.reserve(n - sz);
            for (int i = 0; i < n; i++) if (!inS[i]) cand.push_back(i);

            int v = findVertexToAdd(cand, fS);
            inS[v] = 1;
            ++sz;
        }
    }
    return 0;
}