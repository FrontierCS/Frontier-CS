#include <bits/stdc++.h>
using namespace std;

static void die() {
    fflush(stdout);
    exit(0);
}

static void printVec(const vector<int>& v) {
    for (int i = 0; i < (int)v.size(); i++) {
        if (i) putchar(' ');
        printf("%d", v[i]);
    }
    putchar('\n');
}

static int ask(const vector<int>& L, const vector<int>& R) {
    int l = (int)L.size(), r = (int)R.size();
    printf("? %d %d\n", l, r);
    printVec(L);
    printVec(R);
    fflush(stdout);

    int F;
    if (scanf("%d", &F) != 1) die();
    if (F < -1 || F > 1) die(); // includes -2 on invalid
    return F;
}

static void answer(const vector<int>& demag) {
    printf("! %d", (int)demag.size());
    for (int x : demag) printf(" %d", x);
    putchar('\n');
    fflush(stdout);
}

int main() {
    int t;
    if (scanf("%d", &t) != 1) return 0;

    while (t--) {
        int n;
        if (scanf("%d", &n) != 1) return 0;

        vector<char> isDemag(n + 1, 0);

        int ref = -1;

        // Phase 1: try adjacent pairs to find two non-demagnetized magnets quickly
        for (int i = 1; i + 1 <= n; i += 2) {
            int f = ask(vector<int>{i}, vector<int>{i + 1});
            if (f != 0) {
                ref = i;
                break;
            }
        }

        if (ref != -1) {
            // We have a confirmed non-demagnetized ref
            for (int i = 1; i <= n; i++) {
                if (i == ref) continue;
                int f = ask(vector<int>{ref}, vector<int>{i});
                if (f == 0) isDemag[i] = 1;
            }
            vector<int> demag;
            demag.reserve(n);
            for (int i = 1; i <= n; i++) if (isDemag[i]) demag.push_back(i);
            answer(demag);
            continue;
        }

        // Phase 2: all adjacent pairs gave 0 => each such pair contains at least one demagnetized magnet
        // Build disjoint groups (pairs with internal force 0, plus possible last singleton)
        vector<vector<int>> groups;
        groups.reserve((n + 1) / 2);
        for (int i = 1; i <= n; i += 2) {
            if (i == n) groups.push_back(vector<int>{i});
            else groups.push_back(vector<int>{i, i + 1}); // internal query was 0
        }

        int m = (int)groups.size();
        int gi = -1, gj = -1;

        // Find two groups with non-zero net magnetization via group-vs-group query (non-zero means both groups are mixed)
        for (int i = 0; i < m && gi == -1; i++) {
            for (int j = i + 1; j < m; j++) {
                int f = ask(groups[i], groups[j]);
                if (f != 0) {
                    gi = i;
                    gj = j;
                    break;
                }
            }
        }

        if (gi == -1) die(); // Should never happen due to guarantees

        const vector<int>& gRef = groups[gi];

        vector<char> inRef(n + 1, 0);
        for (int x : gRef) inRef[x] = 1;

        vector<int> nonDemag;
        nonDemag.reserve(n);

        // Classify all magnets not in reference group using reference group query
        for (int x = 1; x <= n; x++) {
            if (inRef[x]) continue;
            int f = ask(gRef, vector<int>{x});
            if (f == 0) isDemag[x] = 1;
            else nonDemag.push_back(x);
        }

        // Resolve which element in gRef is demagnetized (if gRef is a pair)
        if ((int)gRef.size() == 2) {
            int y = -1;
            for (int x : nonDemag) { y = x; break; }
            if (y == -1) die(); // gRef has exactly one non-demag, so there must be another elsewhere

            for (int a : gRef) {
                int f = ask(vector<int>{y}, vector<int>{a});
                if (f == 0) isDemag[a] = 1;
            }
        }
        // If gRef is singleton, it's confirmed non-demag, no action needed.

        vector<int> demag;
        demag.reserve(n);
        for (int i = 1; i <= n; i++) if (isDemag[i]) demag.push_back(i);
        answer(demag);
    }

    return 0;
}