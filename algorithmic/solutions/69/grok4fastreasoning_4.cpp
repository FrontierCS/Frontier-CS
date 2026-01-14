#include <bits/stdc++.h>
using namespace std;

struct State {
    int len, link;
    int next[2];
    State() : len(0), link(-1) { next[0] = next[1] = -1; }
};

vector<State> st;
int lastt;

void sam_init() {
    st.clear();
    st.emplace_back();
    lastt = 0;
}

void sam_extend(int c) {
    int cur = st.size();
    st.emplace_back();
    st[cur].len = st[lastt].len + 1;
    int p = lastt;
    while (p >= 0 && st[p].next[c] == -1) {
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
            int cl = st.size();
            st.emplace_back(st[q]);
            st[cl].len = st[p].len + 1;
            st[q].link = cl;
            st[cur].link = cl;
            while (p >= 0 && st[p].next[c] == q) {
                st[p].next[c] = cl;
                p = st[p].link;
            }
        }
    }
    lastt = cur;
}

long long count_distinct() {
    long long res = 0;
    for (size_t i = 1; i < st.size(); ++i) {
        res += (long long)st[i].len - st[st[i].link].len;
    }
    return res;
}

long long get_power(const string& s) {
    sam_init();
    for (char ch : s) {
        int c = (ch == 'X' ? 0 : 1);
        sam_extend(c);
    }
    return count_distinct();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    vector<string> words(n + 1);
    map<long long, pair<int, int>> mp;
    bool good = false;
    int seed = 0;
    const int MAX_SEED = 20;
    while (!good && seed < MAX_SEED) {
        mp.clear();
        good = true;
        for (int i = 1; i <= n; ++i) {
            string& s = words[i];
            s.resize(i);
            for (int j = 0; j < i; ++j) {
                long long val = (long long)j * 1103515245LL + (long long)i * 12345LL + seed;
                s[j] = ((val & 1) == 0 ? 'X' : 'O');
            }
        }
        for (int u = 1; u <= n && good; ++u) {
            for (int v = 1; v <= n && good; ++v) {
                string con = words[u] + words[v];
                long long p = get_power(con);
                if (mp.count(p)) {
                    good = false;
                } else {
                    mp[p] = {u, v};
                }
            }
        }
        if (good && (int)mp.size() == n * n) {
            // good
        } else {
            good = false;
            ++seed;
        }
    }
    // Assume good after tries
    assert(good);
    for (int i = 1; i <= n; ++i) {
        cout << words[i] << '\n';
    }
    cout.flush();
    int q;
    cin >> q;
    for (int qq = 0; qq < q; ++qq) {
        long long p;
        cin >> p;
        auto [u, v] = mp[p];
        cout << u << " " << v << '\n';
        cout.flush();
    }
    return 0;
}