#include <bits/stdc++.h>
using namespace std;

struct State {
    int len, link;
    int next[2];
    State() : len(0), link(-1) {
        next[0] = next[1] = -1;
    }
};

vector<State> st;
int last;

void sam_init() {
    st.clear();
    st.emplace_back();
    last = 0;
}

void sam_extend(int c) {
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

long long count_distinct(const string& s) {
    sam_init();
    long long total = 0;
    for (char ch : s) {
        int c = (ch == 'X' ? 0 : 1);
        sam_extend(c);
        total += st[last].len - st[st[last].link].len;
    }
    return total;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.tie(nullptr);

    int n;
    cin >> n;

    vector<string> words(n + 1);
    for (int i = 1; i <= n; ++i) {
        words[i] = string(i, 'X') + string(n + 1, 'O') + string(n - i, 'X');
        cout << words[i] << '\n';
    }
    cout << flush;

    // Precompute mapping from power to (i,j)
    unordered_map<long long, pair<int, int>> mp;
    mp.reserve(n * n);
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            string s = words[i] + words[j];
            long long p = count_distinct(s);
            mp[p] = {i, j};
        }
    }

    int q;
    cin >> q;
    while (q--) {
        long long p;
        cin >> p;
        auto it = mp.find(p);
        if (it != mp.end()) {
            cout << it->second.first << ' ' << it->second.second << '\n';
        } else {
            // This should not happen if our construction is correct
            // but fallback to any pair (not needed)
            cout << "1 1\n";
        }
        cout << flush;
    }

    return 0;
}