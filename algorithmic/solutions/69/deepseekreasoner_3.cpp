#include <bits/stdc++.h>
using namespace std;

struct SuffixAutomaton {
    struct State {
        int len, link;
        int next[2];
        State() {
            len = 0;
            link = -1;
            next[0] = next[1] = -1;
        }
    };

    vector<State> st;
    int last;

    SuffixAutomaton() {
        st.emplace_back();
        last = 0;
        st[0].len = 0;
        st[0].link = -1;
    }

    void extend(int c) {
        int cur = st.size();
        st.emplace_back();
        st[cur].len = st[last].len + 1;
        int p = last;
        while (p != -1 && st[p].next[c] == -1) {
            st[p].next[c] = cur;
            p = st[p].link;
        }
        if (p == -1) {
            st[cur].link = 0;
        } else {
            int q = st[p].next[c];
            if (st[p].len + 1 == st[q].len) {
                st[cur].link = q;
            } else {
                int clone = st.size();
                st.push_back(st[q]);
                st[clone].len = st[p].len + 1;
                while (p != -1 && st[p].next[c] == q) {
                    st[p].next[c] = clone;
                    p = st[p].link;
                }
                st[q].link = st[cur].link = clone;
            }
        }
        last = cur;
    }

    long long distinct_substrings() const {
        long long ans = 0;
        for (size_t i = 1; i < st.size(); ++i) {
            ans += st[i].len - st[st[i].link].len;
        }
        return ans;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<string> words(n);
    for (int i = 0; i < n; ++i) {
        words[i] = string(i + 1, 'X') + string(2 * (i + 1), 'O');
        cout << words[i] << endl;
    }
    cout.flush();

    // Precompute powers for all ordered pairs
    unordered_map<long long, pair<int, int>> mp;
    mp.reserve(n * n);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            SuffixAutomaton sa;
            for (char c : words[i]) {
                sa.extend(c == 'X' ? 0 : 1);
            }
            for (char c : words[j]) {
                sa.extend(c == 'X' ? 0 : 1);
            }
            long long p = sa.distinct_substrings();
            mp[p] = {i + 1, j + 1};
        }
    }

    int q;
    cin >> q;
    while (q--) {
        long long p;
        cin >> p;
        auto it = mp.find(p);
        if (it == mp.end()) {
            // Should not happen according to problem statement
            // but just in case.
            cout << "1 1" << endl;
        } else {
            cout << it->second.first << " " << it->second.second << endl;
        }
        cout.flush();
    }

    return 0;
}