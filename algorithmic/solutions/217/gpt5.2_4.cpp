#include <bits/stdc++.h>
using namespace std;

static int N, M;
static long long queryCount = 0;
static int answered = 0;

static inline void appendInt(string &s, int x) {
    char buf[16];
    int len = 0;
    if (x == 0) {
        buf[len++] = '0';
    } else {
        char tmp[16];
        int l = 0;
        while (x > 0) {
            tmp[l++] = char('0' + (x % 10));
            x /= 10;
        }
        for (int i = l - 1; i >= 0; --i) buf[len++] = tmp[i];
    }
    s.append(buf, buf + len);
}

static int querySkip(const vector<int> &cur, size_t skipIdx) {
    const int k = (int)cur.size() - 1;
    static string out;
    out.clear();
    out.reserve((size_t)k * 7 + 32);

    out.push_back('?');
    out.push_back(' ');
    appendInt(out, k);
    for (size_t i = 0; i < cur.size(); i++) {
        if (i == skipIdx) continue;
        out.push_back(' ');
        appendInt(out, cur[i]);
    }
    out.push_back('\n');

    fwrite(out.data(), 1, out.size(), stdout);
    fflush(stdout);

    int res;
    if (scanf("%d", &res) != 1) exit(0);
    queryCount++;
    return res;
}

static void outputStick(const vector<int> &stick) {
    static string out;
    out.clear();
    out.reserve(stick.size() * 7 + 32);

    out.push_back('!');
    for (int x : stick) {
        out.push_back(' ');
        appendInt(out, x);
    }
    out.push_back('\n');

    fwrite(out.data(), 1, out.size(), stdout);
    fflush(stdout);

    answered++;
    if (answered == M) exit(0);
}

static pair<vector<int>, vector<int>> splitKeep(vector<int> cur, int keepM) {
    vector<int> removed;
    int targetSize = N * keepM;
    removed.reserve((int)cur.size() - targetSize);

    size_t pos = 0;
    while ((int)cur.size() > targetSize) {
        if (pos >= cur.size()) pos = 0; // safety; should not be needed
        int ans = querySkip(cur, pos);
        if (ans >= keepM) {
            removed.push_back(cur[pos]);
            cur[pos] = cur.back();
            cur.pop_back();
        } else {
            pos++;
        }
    }
    return {move(cur), move(removed)};
}

static void solve(vector<int> items, int m) {
    if (m == 1) {
        outputStick(items);
        return;
    }
    int m1 = m / 2;
    int m2 = m - m1;

    auto [A, B] = splitKeep(move(items), m1);
    solve(move(A), m1);
    solve(move(B), m2);
}

int main() {
    if (scanf("%d %d", &N, &M) != 2) return 0;

    vector<int> all;
    all.reserve((size_t)N * M);
    for (int i = 1; i <= N * M; i++) all.push_back(i);

    solve(move(all), M);
    return 0;
}