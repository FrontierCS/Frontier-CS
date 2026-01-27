#include <bits/stdc++.h>
using namespace std;

static int query_sets(const vector<int>& L, const vector<int>& R) {
    cout << "? " << (int)L.size() << " " << (int)R.size() << "\n";
    for (int i = 0; i < (int)L.size(); i++) {
        if (i) cout << ' ';
        cout << L[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)R.size(); i++) {
        if (i) cout << ' ';
        cout << R[i];
    }
    cout << "\n";
    cout.flush();

    int F;
    if (!(cin >> F)) exit(0);
    if (F == -2) exit(0);
    return F;
}

static int query_single(int a, int b) {
    vector<int> L{a}, R{b};
    return query_sets(L, R);
}

static int find_nonzero_in_group(const vector<int>& G, const vector<int>& OtherNonZeroGroup) {
    vector<int> cand = G;
    while ((int)cand.size() > 1) {
        int mid = (int)cand.size() / 2;
        vector<int> left(cand.begin(), cand.begin() + mid);
        vector<int> right(cand.begin() + mid, cand.end());

        int F = query_sets(left, OtherNonZeroGroup);
        if (F != 0) cand = std::move(left);
        else cand = std::move(right);
    }
    return cand[0];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        vector<vector<int>> st;
        st.reserve(n);
        for (int i = 1; i <= n; i++) st.push_back(vector<int>{i});

        vector<int> A, B;
        while ((int)st.size() >= 2) {
            vector<int> y = std::move(st.back()); st.pop_back();
            vector<int> x = std::move(st.back()); st.pop_back();

            int F = query_sets(x, y);
            if (F == 0) {
                if (x.size() < y.size()) x.swap(y);
                x.insert(x.end(), y.begin(), y.end());
                st.push_back(std::move(x));
            } else {
                A = std::move(x);
                B = std::move(y);
                break;
            }
        }

        // Safety: should always find two non-zero groups
        if (A.empty() || B.empty()) {
            // Fallback: in unexpected case, use last two groups (shouldn't happen)
            if (st.size() >= 2) { A = st[st.size()-2]; B = st[st.size()-1]; }
            else if (st.size() == 1) { A = st[0]; B = vector<int>{ (st[0][0] % n) + 1 }; }
            else { A = vector<int>{1}; B = vector<int>{2}; }
        }

        int a0 = find_nonzero_in_group(A, B);
        // int b0 = find_nonzero_in_group(B, A); // not needed for final classification

        vector<int> demag;
        demag.reserve(n);

        for (int i = 1; i <= n; i++) {
            if (i == a0) continue;
            int F = query_single(a0, i);
            if (F == 0) demag.push_back(i);
        }

        cout << "! " << (int)demag.size();
        for (int x : demag) cout << ' ' << x;
        cout << "\n";
        cout.flush();
    }
    return 0;
}