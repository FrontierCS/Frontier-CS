#include <bits/stdc++.h>
using namespace std;

static int n;

static inline void appendInt(string &s, int x) {
    char buf[16];
    int len = 0;
    if (x == 0) {
        buf[len++] = '0';
    } else {
        int y = x;
        char tmp[16];
        int tlen = 0;
        while (y > 0) {
            tmp[tlen++] = char('0' + (y % 10));
            y /= 10;
        }
        for (int i = tlen - 1; i >= 0; --i) buf[len++] = tmp[i];
    }
    s.append(buf, buf + len);
}

static int ask(const vector<int> &q) {
    string line;
    line.reserve((size_t)n * 5 + 4);
    line.push_back('0');
    for (int i = 1; i <= n; ++i) {
        line.push_back(' ');
        appendInt(line, q[i]);
    }
    line.push_back('\n');
    cout << line;
    cout.flush();

    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "1 1\n";
        cout.flush();
        return 0;
    }

    vector<int> posOfVal(n + 1, -1);
    vector<int> q(n + 1, 2);

    // Find positions of value 1 and 2 using n queries:
    // Query: q[i]=1, others=2
    // Answer is 2 at i=pos(1), 0 at i=pos(2), 1 otherwise.
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) q[j] = 2;
        q[i] = 1;
        int x = ask(q);
        if (x == 2) posOfVal[1] = i;
        else if (x == 0) posOfVal[2] = i;
    }

    if (posOfVal[1] == -1 || posOfVal[2] == -1) return 0;

    vector<int> remPos;
    remPos.reserve(n);
    for (int i = 1; i <= n; ++i) {
        if (i != posOfVal[1] && i != posOfVal[2]) remPos.push_back(i);
    }

    // Use value 2 (known position) as dummy filler.
    int pos2 = posOfVal[2];

    for (int v = 3; v <= n; ++v) {
        int l = 0, r = (int)remPos.size(); // [l, r)
        while (r - l > 1) {
            int mid = (l + r) / 2;

            for (int i = 1; i <= n; ++i) q[i] = 2;
            // q[pos2] is already 2
            for (int idx = l; idx < mid; ++idx) q[remPos[idx]] = v;

            int x = ask(q); // should be 1 or 2
            if (x == 2) {
                r = mid;
            } else {
                l = mid;
            }
        }
        int pos = remPos[l];
        posOfVal[v] = pos;
        remPos.erase(remPos.begin() + l);
    }

    vector<int> perm(n + 1, 0);
    for (int v = 1; v <= n; ++v) perm[posOfVal[v]] = v;

    string out;
    out.reserve((size_t)n * 5 + 4);
    out.push_back('1');
    for (int i = 1; i <= n; ++i) {
        out.push_back(' ');
        appendInt(out, perm[i]);
    }
    out.push_back('\n');
    cout << out;
    cout.flush();
    return 0;
}