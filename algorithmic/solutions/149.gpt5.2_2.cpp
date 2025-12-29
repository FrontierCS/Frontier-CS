#include <bits/stdc++.h>
using namespace std;

static string manhattan_path(int si, int sj, int ti, int tj) {
    string res;
    while (si < ti) { res.push_back('D'); si++; }
    while (si > ti) { res.push_back('U'); si--; }
    while (sj < tj) { res.push_back('R'); sj++; }
    while (sj > tj) { res.push_back('L'); sj--; }
    return res;
}

static vector<long long> parse_lls(const string &line) {
    vector<long long> v;
    stringstream ss(line);
    long long x;
    while (ss >> x) v.push_back(x);
    return v;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string firstLine;
    while (getline(cin, firstLine)) {
        if (!firstLine.empty()) break;
    }
    if (!cin) return 0;

    vector<long long> first = parse_lls(firstLine);
    if (first.empty()) return 0;

    bool looksInteractive = false;
    if (first.size() == 4) {
        looksInteractive = true;
        for (auto x : first) if (x < 0 || x > 29) looksInteractive = false;
    }

    if (!looksInteractive) {
        // Offline-like input: h (30x29) then v (29x30) then 1000 queries (6 ints each).
        // We ignore weights and (a,e), output simple Manhattan paths for each query.
        // first line likely contains 29 ints for h[0][*].
        // Consume remaining weights based on counts.
        long long dummy;

        // Already read first line values as part of h row 0.
        int readInFirst = (int)first.size();
        // Expect 30*29 numbers for h in total.
        int remainingH = 30 * 29 - readInFirst;
        for (int i = 0; i < remainingH; i++) cin >> dummy;

        // v: 29*30 numbers
        for (int i = 0; i < 29 * 30; i++) cin >> dummy;

        for (int k = 0; k < 1000; k++) {
            int si, sj, ti, tj;
            long long a, e;
            if (!(cin >> si >> sj >> ti >> tj >> a >> e)) break;
            cout << manhattan_path(si, sj, ti, tj) << "\n";
        }
        return 0;
    }

    // Interactive-like: process up to 1000 queries, each: si sj ti tj, output path, read result.
    int si = (int)first[0], sj = (int)first[1], ti = (int)first[2], tj = (int)first[3];
    for (int k = 0; k < 1000; k++) {
        string path = manhattan_path(si, sj, ti, tj);
        cout << path << "\n" << flush;

        long long feedback;
        if (!(cin >> feedback)) break;

        if (k == 999) break;
        if (!(cin >> si >> sj >> ti >> tj)) break;
    }
    return 0;
}