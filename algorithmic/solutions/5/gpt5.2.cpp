#include <bits/stdc++.h>
using namespace std;

class FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    unsigned char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline bool refill() {
        size = fread(buf, 1, BUFSIZE, stdin);
        idx = 0;
        return size > 0;
    }

public:
    template <class T>
    bool readInt(T &out) {
        out = 0;
        T sign = 1;
        unsigned char c;
        do {
            if (idx >= size && !refill()) return false;
            c = buf[idx++];
        } while (c <= ' ');

        if (c == '-') {
            sign = -1;
            if (idx >= size && !refill()) return false;
            c = buf[idx++];
        }
        for (; c > ' '; ) {
            out = out * 10 + (c - '0');
            if (idx >= size) {
                if (!refill()) break;
            }
            c = buf[idx++];
        }
        out *= sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    // Read and ignore scoring parameters.
    for (int i = 0; i < 10; i++) {
        int x; fs.readInt(x);
    }

    vector<int> head(n + 1, -1), rhead(n + 1, -1);
    vector<int> to(m), nxt(m), rto(m), rnxt(m);
    vector<int> outdeg(n + 1, 0);

    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u); fs.readInt(v);

        to[i] = v;
        nxt[i] = head[u];
        head[u] = i;

        rto[i] = u;
        rnxt[i] = rhead[v];
        rhead[v] = i;

        outdeg[u]++;
    }

    int start = 1;
    for (int v = 2; v <= n; v++) {
        if (outdeg[v] > outdeg[start]) start = v;
    }

    vector<char> vis(n + 1, 0);
    vector<int> outPtr = head, inPtr = rhead;

    deque<int> path;
    path.push_back(start);
    vis[start] = 1;

    int first = start, last = start;

    bool progress = true;
    while (progress) {
        progress = false;

        // Extend forward
        while (true) {
            int &e = outPtr[last];
            while (e != -1 && vis[to[e]]) e = nxt[e];
            if (e == -1) break;
            int nx = to[e];
            e = nxt[e];
            if (!vis[nx]) {
                vis[nx] = 1;
                path.push_back(nx);
                last = nx;
                progress = true;
            }
        }

        // Extend backward
        while (true) {
            int &e = inPtr[first];
            while (e != -1 && vis[rto[e]]) e = rnxt[e];
            if (e == -1) break;
            int pr = rto[e];
            e = rnxt[e];
            if (!vis[pr]) {
                vis[pr] = 1;
                path.push_front(pr);
                first = pr;
                progress = true;
            }
        }
    }

    cout << path.size() << "\n";
    for (size_t i = 0; i < path.size(); i++) {
        if (i) cout << ' ';
        cout << path[i];
    }
    cout << "\n";
    return 0;
}