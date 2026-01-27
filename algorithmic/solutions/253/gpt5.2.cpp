#include <bits/stdc++.h>
using namespace std;

static void die() {
    exit(0);
}

static void print_flush(const string &s) {
    cout << s << '\n';
    cout.flush();
}

static int read_int_or_die() {
    int x;
    if (!(cin >> x)) die();
    if (x == -1) die();
    return x;
}

static void block_edge(int idx) {
    print_flush("- " + to_string(idx));
}

static void unblock_edge(int idx) {
    print_flush("+ " + to_string(idx));
}

static int query_single(int y) {
    print_flush("? 1 " + to_string(y));
    return read_int_or_die();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    while (t--) {
        int n, m;
        cin >> n >> m;
        vector<int> a(m + 1), b(m + 1);
        for (int i = 1; i <= m; i++) cin >> a[i] >> b[i];

        // Block all edges first
        for (int i = 1; i <= m; i++) block_edge(i);

        vector<int> repaired(m + 1, 0);

        // Test each edge individually: unblock it alone and check reachability between endpoints
        for (int i = 1; i <= m; i++) {
            unblock_edge(i);

            // Sync starting intersection to a[i]
            (void)query_single(a[i]);

            // Now test reachability to b[i]
            int ans = query_single(b[i]);
            repaired[i] = ans ? 1 : 0;

            block_edge(i);
        }

        {
            ostringstream oss;
            oss << "!";
            for (int i = 1; i <= m; i++) oss << ' ' << repaired[i];
            print_flush(oss.str());
        }

        int verdict = read_int_or_die();
        if (verdict != 1) die();
    }

    return 0;
}