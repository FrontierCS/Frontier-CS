#include <bits/stdc++.h>
using namespace std;

int N;
string S;
vector<int> Cost, ChoiceJ, BType;
long long Pow3[16];

int compute_id(int m0, int m1) {
    int id = 0;
    long long p = 1;
    for (int i = 0; i < N; i++) {
        int st = 2;
        if (m0 & (1 << i)) st = 0;
        else if (m1 & (1 << i)) st = 1;
        id += st * p;
        p *= 3;
    }
    return id;
}

bool is_const1(int m0, int m1) {
    int pos = 0;
    for (int i = 0; i < N; i++) {
        if (m1 & (1 << i)) pos += (1 << i);
    }
    return S[pos] == '1';
}

bool is_const0(int m0, int m1) {
    int pos = 0;
    for (int i = 0; i < N; i++) {
        if ((m0 & (1 << i)) == 0) pos += (1 << i);
    }
    return S[pos] == '0';
}

int dp(int m0, int m1);

string build(int m0, int m1) {
    int used = m0 | m1;
    int fcnt = N - __builtin_popcount(used);
    if (fcnt == 0) {
        int pos = 0;
        for (int i = 0; i < N; i++) {
            if (m1 & (1 << i)) pos += (1 << i);
        }
        return S[pos] == '1' ? "T" : "F";
    }
    if (is_const1(m0, m1)) return "T";
    if (is_const0(m0, m1)) return "F";
    if (fcnt == 1) {
        int j = 0;
        while ((used & (1 << j))) j++;
        return string(1, 'a' + j);
    }
    int id = compute_id(m0, m1);
    int typ = BType[id];
    int j = ChoiceJ[id];
    int m0_0 = m0 | (1 << j);
    int m1_0 = m1;
    int m0_1 = m0;
    int m1_1 = m1 | (1 << j);
    string e0 = build(m0_0, m1_0);
    string e1 = build(m0_1, m1_1);
    string v(1, 'a' + j);
    if (typ == 0) return "F";
    if (typ == 1) return "T";
    if (typ == 2) return v;
    if (typ == 3) {
        string inner = "(" + v + "&" + e1 + ")";
        return "(" + e0 + "|" + inner + ")";
    }
    if (typ == 4) {
        return "(" + v + "&" + e1 + ")";
    }
    if (typ == 5) {
        return "(" + e0 + "|" + v + ")";
    }
    if (typ == 6) {
        return v;
    }
    if (typ == 7) {
        return e0;
    }
    assert(false);
    return "";
}

int dp(int m0, int m1) {
    int id = compute_id(m0, m1);
    if (Cost[id] != -1) return Cost[id];
    int used = m0 | m1;
    int fcnt = N - __builtin_popcount(used);
    if (fcnt == 0) {
        int pos = 0;
        for (int i = 0; i < N; i++) {
            if (m1 & (1 << i)) pos += (1 << i);
        }
        bool is1 = (S[pos] == '1');
        Cost[id] = 0;
        BType[id] = is1 ? 1 : 0;
        return 0;
    }
    if (is_const1(m0, m1)) {
        Cost[id] = 0;
        BType[id] = 1;
        return 0;
    }
    if (is_const0(m0, m1)) {
        Cost[id] = 0;
        BType[id] = 0;
        return 0;
    }
    if (fcnt == 1) {
        int j = 0;
        while ((used & (1 << j))) j++;
        Cost[id] = 0;
        BType[id] = 2;
        ChoiceJ[id] = j;
        return 0;
    }
    // fcnt >=2, not const
    int minc = INT_MAX;
    int bestj = -1;
    int besttyp = -1;
    for (int jj = 0; jj < N; jj++) {
        if (used & (1 << jj)) continue;
        int m0_0 = m0 | (1 << jj);
        int m1_0 = m1;
        int m0_1 = m0;
        int m1_1 = m1 | (1 << jj);
        int c0 = dp(m0_0, m1_0);
        int c1 = dp(m0_1, m1_1);
        bool e0_F = is_const0(m0_0, m1_0);
        bool e0_T = is_const1(m0_0, m1_0);
        bool e1_F = is_const0(m0_1, m1_1);
        bool e1_T = is_const1(m0_1, m1_1);
        int thisc;
        int thistyp;
        if (e0_T) {
            thisc = 0;
            thistyp = 1;
        } else if (e0_F) {
            if (e1_T) {
                thisc = 0;
                thistyp = 6;
            } else {
                thisc = c1 + 1;
                thistyp = 4;
            }
        } else if (e1_F) {
            thisc = c0;
            thistyp = 7;
        } else if (e1_T) {
            thisc = c0 + 1;
            thistyp = 5;
        } else {
            thisc = c0 + c1 + 2;
            thistyp = 3;
        }
        if (thisc < minc) {
            minc = thisc;
            bestj = jj;
            besttyp = thistyp;
        }
    }
    Cost[id] = minc;
    ChoiceJ[id] = bestj;
    BType[id] = besttyp;
    return minc;
}

bool check_mono() {
    for (int i = 0; i < N; i++) {
        int bit = 1 << i;
        for (int mask = 0; mask < (1 << N); mask++) {
            if ((mask & bit) == 0) {
                int p0 = mask;
                int p1 = mask | bit;
                if (S[p0] == '1' && S[p1] == '0') return false;
            }
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int T;
    cin >> T;
    Pow3[0] = 1;
    for (int i = 1; i <= 15; i++) Pow3[i] = Pow3[i - 1] * 3;
    for (int t = 0; t < T; t++) {
        cin >> N;
        cin >> S;
        bool mono = check_mono();
        if (!mono) {
            cout << "No\n";
            continue;
        }
        int pow3n = Pow3[N];
        Cost.assign(pow3n, -1);
        ChoiceJ.assign(pow3n, -1);
        BType.assign(pow3n, -1);
        dp(0, 0);
        cout << "Yes\n";
        string expr = build(0, 0);
        cout << expr << "\n";
    }
    return 0;
}