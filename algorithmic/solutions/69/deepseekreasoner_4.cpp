#include <bits/stdc++.h>
using namespace std;

struct State {
    int len, link;
    int next[2];
};

const int MAX_STATES = 10000; // Enough for strings up to 5000

static State st[MAX_STATES];
static int sz, last;

void sa_init() {
    st[0].len = 0;
    st[0].link = -1;
    st[0].next[0] = st[0].next[1] = -1;
    sz = 1;
    last = 0;
}

void sa_extend(int c, long long& total) {
    int cur = sz++;
    st[cur].len = st[last].len + 1;
    st[cur].next[0] = st[cur].next[1] = -1;
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
            int clone = sz++;
            st[clone].len = st[p].len + 1;
            st[clone].next[0] = st[q].next[0];
            st[clone].next[1] = st[q].next[1];
            st[clone].link = st[q].link;
            while (p != -1 && st[p].next[c] == q) {
                st[p].next[c] = clone;
                p = st[p].link;
            }
            st[q].link = st[cur].link = clone;
        }
    }
    last = cur;
    total += st[cur].len - st[st[cur].link].len;
}

long long count_distinct_substrings(const string& s) {
    sa_init();
    long long total = 0;
    for (char ch : s) {
        int c = (ch == 'X') ? 0 : 1;
        sa_extend(c, total);
    }
    return total;
}

// deterministic pseudo-random string generation
string generate_word(int id, int len) {
    string res(len, ' ');
    unsigned int state = id * 123456789; // seed based on id
    for (int i = 0; i < len; ++i) {
        state = state * 1103515245 + 12345;
        int bit = (state >> 10) & 1;
        res[i] = bit ? 'X' : 'O';
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    int L = min(500, 30 * n);
    vector<string> words(n + 1);
    for (int i = 1; i <= n; ++i) {
        words[i] = generate_word(i, L);
    }

    // output the words
    for (int i = 1; i <= n; ++i) {
        cout << words[i] << endl;
    }
    cout.flush();

    // precompute all powers and build map
    unordered_map<long long, pair<int, int>> mp;
    mp.reserve(n * n);
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            string s = words[i] + words[j];
            long long p = count_distinct_substrings(s);
            mp[p] = {i, j};
        }
    }

    int q;
    cin >> q;
    while (q--) {
        long long p;
        cin >> p;
        auto& ans = mp.at(p);
        cout << ans.first << ' ' << ans.second << endl;
        cout.flush();
    }

    return 0;
}