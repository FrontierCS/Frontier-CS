#include <cstdio>
#include <vector>
#include <algorithm>
#include <cassert>

using namespace std;

int ask(int u, int v) {
    printf("? %d %d\n", u, v);
    fflush(stdout);
    int d;
    scanf("%d", &d);
    return d;
}

int main() {
    int n;
    scanf("%d", &n);

    // Step 1: find one endpoint of the diameter by querying from node 1
    vector<int> dist1(n+1, 0);
    for (int v = 2; v <= n; ++v) {
        dist1[v] = ask(1, v);
    }
    int a = 1;
    for (int v = 2; v <= n; ++v) {
        if (dist1[v] > dist1[a]) {
            a = v;
        }
    }

    // Step 2: query from a to all nodes, find the other endpoint b
    vector<int> distA(n+1, 0);
    for (int v = 1; v <= n; ++v) {
        if (v == a) continue;
        distA[v] = ask(a, v);
    }
    int b = 1;
    for (int v = 2; v <= n; ++v) {
        if (distA[v] > distA[b]) {
            b = v;
        }
    }

    // Step 3: query from b to all nodes
    vector<int> distB(n+1, 0);
    for (int v = 1; v <= n; ++v) {
        if (v == b) continue;
        distB[v] = ask(b, v);
    }

    int D = distA[b];  // distance between a and b

    // Step 4: identify nodes on the path from a to b
    vector<int> dist_to_node(D+1, -1);
    for (int v = 1; v <= n; ++v) {
        if (distA[v] + distB[v] == D) {
            dist_to_node[distA[v]] = v;
        }
    }
    // Every distance from 0 to D should be present
    for (int i = 0; i <= D; ++i) {
        assert(dist_to_node[i] != -1);
    }

    // Step 5: compute size of attachment for each node on the path
    vector<int> size(D+1, 0);
    for (int v = 1; v <= n; ++v) {
        long long d_diff = distA[v] - distB[v];
        long long key = (D + d_diff) / 2;  // must be integer
        // key is distance from a of the attachment point w
        size[key]++;
    }

    // Step 6: compute prefix sums (left side sizes)
    vector<long long> pref(D+2, 0);
    for (int i = 0; i <= D; ++i) {
        pref[i+1] = pref[i] + size[i];
    }
    // pref[i] = sum_{j=0}^{i-1} size[j]  (nodes strictly left of distance i)

    // Step 7: find centroid
    int centroid = -1;
    for (int i = 0; i <= D; ++i) {
        long long left = pref[i];                 // nodes with distA < i
        long long right = n - pref[i] - size[i];  // nodes with distA > i
        if (left <= n/2 && right <= n/2) {
            centroid = dist_to_node[i];
            break;
        }
    }
    assert(centroid != -1);

    printf("! %d\n", centroid);
    fflush(stdout);

    return 0;
}