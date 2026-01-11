#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <unordered_map>
#include <set>
#include <limits>

using namespace std;

const double INF = 1e18;

struct Point {
    double x, y;
    int id;
};

struct Device {
    int id, x, y;
    char type;
};

// KD-Tree for nearest neighbor search among relays
struct KDNode {
    Point p;
    int axis; // 0: x, 1: y
    KDNode *left, *right;
    KDNode(Point _p, int _axis) : p(_p), axis(_axis), left(nullptr), right(nullptr) {}
};

double sqdist(const Point& a, const Point& b) {
    double dx = a.x - b.x;
    double dy = a.y - b.y;
    return dx*dx + dy*dy;
}

KDNode* buildKDTree(vector<Point>& points, int depth) {
    if (points.empty()) return nullptr;
    int axis = depth % 2;
    if (axis == 0)
        sort(points.begin(), points.end(), [](const Point& a, const Point& b) { return a.x < b.x; });
    else
        sort(points.begin(), points.end(), [](const Point& a, const Point& b) { return a.y < b.y; });
    int mid = points.size() / 2;
    KDNode* node = new KDNode(points[mid], axis);
    vector<Point> leftPoints(points.begin(), points.begin() + mid);
    vector<Point> rightPoints(points.begin() + mid + 1, points.end());
    node->left = buildKDTree(leftPoints, depth + 1);
    node->right = buildKDTree(rightPoints, depth + 1);
    return node;
}

void nearestNeighbor(KDNode* node, const Point& query, double& bestDist, Point& bestPoint) {
    if (!node) return;
    double d = sqdist(node->p, query);
    if (d < bestDist) {
        bestDist = d;
        bestPoint = node->p;
    }
    int axis = node->axis;
    double diff = axis == 0 ? query.x - node->p.x : query.y - node->p.y;
    KDNode* first = diff <= 0 ? node->left : node->right;
    KDNode* second = diff <= 0 ? node->right : node->left;
    nearestNeighbor(first, query, bestDist, bestPoint);
    if (diff * diff < bestDist) {
        nearestNeighbor(second, query, bestDist, bestPoint);
    }
}

int findNearestRelay(KDNode* root, double mx, double my) {
    Point query = {mx, my, -1};
    double bestDist = INF;
    Point bestPoint;
    nearestNeighbor(root, query, bestDist, bestPoint);
    return bestPoint.id;
}

// DSU for Kruskal
struct DSU {
    vector<int> parent, rank;
    DSU(int n) {
        parent.resize(n);
        rank.resize(n, 0);
        for (int i = 0; i < n; ++i) parent[i] = i;
    }
    int find(int x) {
        if (parent[x] != x) parent[x] = find(parent[x]);
        return parent[x];
    }
    bool unite(int x, int y) {
        x = find(x); y = find(y);
        if (x == y) return false;
        if (rank[x] < rank[y]) parent[x] = y;
        else if (rank[x] > rank[y]) parent[y] = x;
        else { parent[y] = x; rank[x]++; }
        return true;
    }
};

double computeEdgeCost(const Device& a, const Device& b) {
    long long dx = a.x - b.x;
    long long dy = a.y - b.y;
    long long d2 = dx*dx + dy*dy;
    double factor;
    if (a.type == 'C' || b.type == 'C') factor = 1.0;
    else if (a.type == 'S' || b.type == 'S') factor = 0.8;
    else factor = 1.0;
    return factor * d2;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    cin >> N >> K;
    vector<Device> robots, relays;
    unordered_map<int, Device> idToDevice; // all devices

    for (int i = 0; i < N + K; ++i) {
        int id, x, y;
        char type;
        cin >> id >> x >> y >> type;
        Device dev = {id, x, y, type};
        idToDevice[id] = dev;
        if (type == 'C') {
            relays.push_back(dev);
        } else {
            robots.push_back(dev);
        }
    }

    // Build KD-Tree for relays
    KDNode* kdRoot = nullptr;
    if (K > 0) {
        vector<Point> relayPoints;
        for (const auto& r : relays) {
            relayPoints.push_back({(double)r.x, (double)r.y, r.id});
        }
        kdRoot = buildKDTree(relayPoints, 0);
    }

    int nRobots = robots.size();
    // Matrix for min cost between robots and whether via a relay
    vector<vector<double>> minCost(nRobots, vector<double>(nRobots, INF));
    vector<vector<int>> viaRelay(nRobots, vector<int>(nRobots, -1));

    // Precompute pairwise min distances (direct or via one relay)
    for (int i = 0; i < nRobots; ++i) {
        for (int j = i+1; j < nRobots; ++j) {
            const Device& a = robots[i];
            const Device& b = robots[j];
            // Direct cost
            long long dx = a.x - b.x;
            long long dy = a.y - b.y;
            long long d2 = dx*dx + dy*dy;
            double direct;
            if (a.type == 'R' && b.type == 'R') direct = d2;
            else direct = 0.8 * d2; // at least one S

            // Via relay cost
            double via = INF;
            int bestRelayIdx = -1;
            if (K > 0) {
                double mx = (a.x + b.x) / 2.0;
                double my = (a.y + b.y) / 2.0;
                int nearestId = findNearestRelay(kdRoot, mx, my);
                // find relay by id
                const Device* relay = nullptr;
                for (int idx = 0; idx < relays.size(); ++idx) {
                    if (relays[idx].id == nearestId) {
                        relay = &relays[idx];
                        bestRelayIdx = idx;
                        break;
                    }
                }
                if (relay) {
                    long long d2_ic = (a.x - relay->x)*(a.x - relay->x) + (a.y - relay->y)*(a.y - relay->y);
                    long long d2_jc = (b.x - relay->x)*(b.x - relay->x) + (b.y - relay->y)*(b.y - relay->y);
                    via = d2_ic + d2_jc; // factor 1.0
                }
            }

            if (via <= direct) { // prefer via if equal
                minCost[i][j] = minCost[j][i] = via;
                viaRelay[i][j] = viaRelay[j][i] = bestRelayIdx;
            } else {
                minCost[i][j] = minCost[j][i] = direct;
                viaRelay[i][j] = viaRelay[j][i] = -1;
            }
        }
    }

    // Prim's MST on robots using minCost
    vector<bool> inMST(nRobots, false);
    vector<double> key(nRobots, INF);
    vector<int> parent(nRobots, -1);
    key[0] = 0.0;
    vector<pair<int,int>> mstEdges; // indices in robots array

    for (int iter = 0; iter < nRobots; ++iter) {
        int u = -1;
        double minKey = INF;
        for (int i = 0; i < nRobots; ++i) {
            if (!inMST[i] && key[i] < minKey) {
                minKey = key[i];
                u = i;
            }
        }
        inMST[u] = true;
        if (parent[u] != -1) {
            mstEdges.emplace_back(parent[u], u);
        }
        for (int v = 0; v < nRobots; ++v) {
            if (!inMST[v] && minCost[u][v] < key[v]) {
                key[v] = minCost[u][v];
                parent[v] = u;
            }
        }
    }

    // Expand MST edges to actual edges (direct or via relay)
    set<pair<int,int>> edgeSet; // store unique edges (smaller id first)
    set<int> usedRelayIds; // relay ids that appear in expanded edges

    for (auto& e : mstEdges) {
        int u = e.first, v = e.second;
        int relayIdx = viaRelay[u][v];
        if (relayIdx != -1) {
            const Device& relay = relays[relayIdx];
            usedRelayIds.insert(relay.id);
            int idU = robots[u].id;
            int idV = robots[v].id;
            edgeSet.insert({min(idU, relay.id), max(idU, relay.id)});
            edgeSet.insert({min(idV, relay.id), max(idV, relay.id)});
        } else {
            int idU = robots[u].id;
            int idV = robots[v].id;
            edgeSet.insert({min(idU, idV), max(idU, idV)});
        }
    }

    // Prepare nodes and edges for final MST (Kruskal)
    vector<int> nodeIds;
    for (const auto& r : robots) nodeIds.push_back(r.id);
    for (int rid : usedRelayIds) nodeIds.push_back(rid);
    sort(nodeIds.begin(), nodeIds.end());
    unordered_map<int, int> idToIndex;
    int numNodes = nodeIds.size();
    for (int i = 0; i < numNodes; ++i) idToIndex[nodeIds[i]] = i;

    vector<pair<double, pair<int,int>>> edgesWithWeight;
    for (const auto& edge : edgeSet) {
        int a = edge.first, b = edge.second;
        double w = computeEdgeCost(idToDevice[a], idToDevice[b]);
        edgesWithWeight.push_back({w, {a, b}});
    }
    sort(edgesWithWeight.begin(), edgesWithWeight.end());

    DSU dsu(numNodes);
    vector<pair<int,int>> finalEdges;
    set<int> finalRelays;
    for (auto& ew : edgesWithWeight) {
        int a = ew.second.first, b = ew.second.second;
        int ia = idToIndex[a], ib = idToIndex[b];
        if (dsu.unite(ia, ib)) {
            finalEdges.emplace_back(a, b);
            if (idToDevice[a].type == 'C') finalRelays.insert(a);
            if (idToDevice[b].type == 'C') finalRelays.insert(b);
        }
    }

    // Output
    if (finalRelays.empty()) {
        cout << "#\n";
    } else {
        bool first = true;
        for (int rid : finalRelays) {
            if (!first) cout << "#";
            cout << rid;
            first = false;
        }
        cout << "\n";
    }
    // Edges
    bool first = true;
    for (auto& e : finalEdges) {
        if (!first) cout << "#";
        cout << e.first << "-" << e.second;
        first = false;
    }
    cout << "\n";

    // Cleanup KD-Tree (optional, omitted for brevity)
    return 0;
}