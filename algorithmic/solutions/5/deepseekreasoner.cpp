#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500000;
int parent[MAXN], sizeComp[MAXN], nxt[MAXN], prv[MAXN], compStart[MAXN], compEnd[MAXN];
bool isEndpoint[MAXN];

int find(int x) {
    return parent[x] == x ? x : parent[x] = find(parent[x]);
}

void reverseComponent(int r) {
    int cur = compStart[r];
    while (cur != -1) {
        swap(nxt[cur], prv[cur]);
        cur = prv[cur]; // after swap, prv holds the original next
    }
    swap(compStart[r], compEnd[r]);
}

void merge(int u, int v, int ru, int rv) {
    nxt[u] = v;
    prv[v] = u;
    isEndpoint[u] = false;
    isEndpoint[v] = false;
    int start_u = compStart[ru];
    int end_v = compEnd[rv];
    if (sizeComp[ru] < sizeComp[rv]) {
        swap(ru, rv);
    }
    parent[rv] = ru;
    sizeComp[ru] += sizeComp[rv];
    compStart[ru] = start_u;
    compEnd[ru] = end_v;
}

int main() {
    int n, m;
    scanf("%d %d", &n, &m);
    vector<int> a(10);
    for (int i = 0; i < 10; ++i) scanf("%d", &a[i]); // ignored in the algorithm

    vector<pair<int, int>> edges;
    for (int i = 0; i < m; ++i) {
        int u, v;
        scanf("%d %d", &u, &v);
        --u; --v;
        edges.emplace_back(u, v);
    }

    // sort edges by destination, then source
    sort(edges.begin(), edges.end(), [](const pair<int, int>& p1, const pair<int, int>& p2) {
        if (p1.second != p2.second) return p1.second < p2.second;
        return p1.first < p2.first;
    });

    // initialize DSU and path structures
    for (int i = 0; i < n; ++i) {
        parent[i] = i;
        sizeComp[i] = 1;
        nxt[i] = -1;
        prv[i] = -1;
        isEndpoint[i] = true;
        compStart[i] = i;
        compEnd[i] = i;
    }

    // up to 10 passes
    for (int iter = 0; iter < 10; ++iter) {
        bool changed = false;
        for (const auto& e : edges) {
            int u = e.first, v = e.second;
            int ru = find(u), rv = find(v);
            if (ru == rv) continue;
            if (!isEndpoint[u] || !isEndpoint[v]) continue;

            bool u_start = (prv[u] == -1);
            bool u_end = (nxt[u] == -1);
            bool v_start = (prv[v] == -1);
            bool v_end = (nxt[v] == -1);

            if (u_end && v_start) {
                merge(u, v, ru, rv);
                changed = true;
            } else if (u_start && v_end) {
                reverseComponent(ru);
                reverseComponent(rv);
                merge(u, v, ru, rv);
                changed = true;
            } else if (u_end && v_end) {
                reverseComponent(rv);
                merge(u, v, ru, rv);
                changed = true;
            } else if (u_start && v_start) {
                reverseComponent(ru);
                merge(u, v, ru, rv);
                changed = true;
            }
        }
        if (!changed) break;
    }

    // find the largest component
    int bestRoot = -1, bestSize = 0;
    for (int i = 0; i < n; ++i) {
        if (find(i) == i) {
            if (sizeComp[i] > bestSize) {
                bestSize = sizeComp[i];
                bestRoot = i;
            }
        }
    }

    // reconstruct the path
    vector<int> path;
    int cur = compStart[bestRoot];
    while (cur != -1) {
        path.push_back(cur);
        cur = nxt[cur];
    }

    // output
    printf("%d\n", (int)path.size());
    for (size_t i = 0; i < path.size(); ++i) {
        if (i) printf(" ");
        printf("%d", path[i] + 1);
    }
    printf("\n");

    return 0;
}