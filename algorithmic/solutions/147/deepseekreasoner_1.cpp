#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

const int GRID = 10000;

struct Company {
    int id, x, y, r;
};

int n;
vector<Company> comps;
vector<vector<int>> rects; // each: a,b,c,d

struct Node {
    bool leaf;
    int company_id; // for leaf
    int lx, rx, ly, ry;
    // for internal
    bool vertical;
    int split;
    int low_bound, high_bound; // allowed range for split
    Node* left;
    Node* right;
    Node() : leaf(false), left(nullptr), right(nullptr) {}
};

vector<Node*> internal_nodes;
vector<Node*> leaf_nodes;

Node* build(int lx, int rx, int ly, int ry, vector<int>& idxs) {
    Node* node = new Node();
    node->lx = lx; node->rx = rx; node->ly = ly; node->ry = ry;
    if (idxs.size() == 1) {
        node->leaf = true;
        node->company_id = idxs[0];
        leaf_nodes.push_back(node);
        return node;
    }
    int m = idxs.size();
    long long total_r = 0;
    for (int idx : idxs) total_r += comps[idx].r;
    double A = (double)(rx - lx) * (ry - ly);
    double best_cost = 1e30;
    bool best_vertical = true;
    int best_split_idx = -1;
    int best_split_coord = -1;

    // Try vertical split
    vector<int> sorted = idxs;
    sort(sorted.begin(), sorted.end(), [&](int i, int j) { return comps[i].x < comps[j].x; });
    vector<long long> prefix(m+1, 0);
    for (int i = 0; i < m; ++i) prefix[i+1] = prefix[i] + comps[sorted[i]].r;
    for (int i = 1; i < m; ++i) {
        // left: 0..i-1, right: i..m-1
        int max_left_x_plus1 = 0;
        for (int j = 0; j < i; ++j) {
            int xj = comps[sorted[j]].x;
            max_left_x_plus1 = max(max_left_x_plus1, xj + 1);
        }
        int min_right_x = GRID;
        for (int j = i; j < m; ++j) {
            int xj = comps[sorted[j]].x;
            min_right_x = min(min_right_x, xj);
        }
        if (max_left_x_plus1 > min_right_x) continue;
        long long R1 = prefix[i];
        double target = lx + (double)R1 * (rx - lx) / total_r;
        int X = round(target);
        if (X < max_left_x_plus1) X = max_left_x_plus1;
        if (X > min_right_x) X = min_right_x;
        double left_area = (X - lx) * (ry - ly);
        double desired_left_area = R1 * A / total_r;
        double cost = abs(left_area - desired_left_area);
        if (cost < best_cost) {
            best_cost = cost;
            best_vertical = true;
            best_split_idx = i;
            best_split_coord = X;
        }
    }

    // Try horizontal split
    sorted = idxs;
    sort(sorted.begin(), sorted.end(), [&](int i, int j) { return comps[i].y < comps[j].y; });
    prefix.assign(m+1, 0);
    for (int i = 0; i < m; ++i) prefix[i+1] = prefix[i] + comps[sorted[i]].r;
    for (int i = 1; i < m; ++i) {
        int max_left_y_plus1 = 0;
        for (int j = 0; j < i; ++j) {
            int yj = comps[sorted[j]].y;
            max_left_y_plus1 = max(max_left_y_plus1, yj + 1);
        }
        int min_right_y = GRID;
        for (int j = i; j < m; ++j) {
            int yj = comps[sorted[j]].y;
            min_right_y = min(min_right_y, yj);
        }
        if (max_left_y_plus1 > min_right_y) continue;
        long long R1 = prefix[i];
        double target = ly + (double)R1 * (ry - ly) / total_r;
        int Y = round(target);
        if (Y < max_left_y_plus1) Y = max_left_y_plus1;
        if (Y > min_right_y) Y = min_right_y;
        double bottom_area = (Y - ly) * (rx - lx);
        double desired_bottom_area = R1 * A / total_r;
        double cost = abs(bottom_area - desired_bottom_area);
        if (cost < best_cost) {
            best_cost = cost;
            best_vertical = false;
            best_split_idx = i;
            best_split_coord = Y;
        }
    }

    if (best_split_idx == -1) {
        // fallback: split vertically at median x
        sorted = idxs;
        sort(sorted.begin(), sorted.end(), [&](int i, int j) { return comps[i].x < comps[j].x; });
        int i = m / 2;
        best_vertical = true;
        best_split_idx = i;
        int max_left_x_plus1 = 0;
        for (int j = 0; j < i; ++j) max_left_x_plus1 = max(max_left_x_plus1, comps[sorted[j]].x + 1);
        int min_right_x = GRID;
        for (int j = i; j < m; ++j) min_right_x = min(min_right_x, comps[sorted[j]].x);
        if (max_left_x_plus1 <= min_right_x) {
            best_split_coord = (max_left_x_plus1 + min_right_x) / 2;
        } else {
            best_split_coord = (lx + rx) / 2;
        }
    }

    // Perform the split
    node->leaf = false;
    node->vertical = best_vertical;
    node->split = best_split_coord;
    vector<int> left_idxs, right_idxs;
    if (best_vertical) {
        sorted = idxs;
        sort(sorted.begin(), sorted.end(), [&](int i, int j) { return comps[i].x < comps[j].x; });
        left_idxs.assign(sorted.begin(), sorted.begin() + best_split_idx);
        right_idxs.assign(sorted.begin() + best_split_idx, sorted.end());
        int max_left_x_plus1 = 0;
        for (int idx : left_idxs) max_left_x_plus1 = max(max_left_x_plus1, comps[idx].x + 1);
        int min_right_x = GRID;
        for (int idx : right_idxs) min_right_x = min(min_right_x, comps[idx].x);
        node->low_bound = max_left_x_plus1;
        node->high_bound = min_right_x;
        node->left = build(lx, best_split_coord, ly, ry, left_idxs);
        node->right = build(best_split_coord, rx, ly, ry, right_idxs);
    } else {
        sorted = idxs;
        sort(sorted.begin(), sorted.end(), [&](int i, int j) { return comps[i].y < comps[j].y; });
        left_idxs.assign(sorted.begin(), sorted.begin() + best_split_idx);
        right_idxs.assign(sorted.begin() + best_split_idx, sorted.end());
        int max_left_y_plus1 = 0;
        for (int idx : left_idxs) max_left_y_plus1 = max(max_left_y_plus1, comps[idx].y + 1);
        int min_right_y = GRID;
        for (int idx : right_idxs) min_right_y = min(min_right_y, comps[idx].y);
        node->low_bound = max_left_y_plus1;
        node->high_bound = min_right_y;
        node->left = build(lx, rx, ly, best_split_coord, left_idxs);
        node->right = build(lx, rx, best_split_coord, ry, right_idxs);
    }
    internal_nodes.push_back(node);
    return node;
}

void update_rectangles(Node* node, int lx, int rx, int ly, int ry) {
    node->lx = lx; node->rx = rx; node->ly = ly; node->ry = ry;
    if (node->leaf) return;
    if (node->vertical) {
        update_rectangles(node->left, lx, node->split, ly, ry);
        update_rectangles(node->right, node->split, rx, ly, ry);
    } else {
        update_rectangles(node->left, lx, rx, ly, node->split);
        update_rectangles(node->right, lx, rx, node->split, ry);
    }
}

double compute_score() {
    double sum = 0.0;
    for (Node* leaf : leaf_nodes) {
        int s = (leaf->rx - leaf->lx) * (leaf->ry - leaf->ly);
        int r = comps[leaf->company_id].r;
        if (s == 0) continue;
        double t;
        if (s <= r) t = (double)s / r;
        else t = (double)r / s;
        double p = 1.0 - (1.0 - t) * (1.0 - t);
        sum += p;
    }
    return sum;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;
    comps.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> comps[i].x >> comps[i].y >> comps[i].r;
        comps[i].id = i;
    }

    rects.assign(n, vector<int>(4));

    vector<int> idxs(n);
    for (int i = 0; i < n; ++i) idxs[i] = i;

    leaf_nodes.clear();
    internal_nodes.clear();
    Node* root = build(0, GRID, 0, GRID, idxs);

    // Initial rectangles
    update_rectangles(root, 0, GRID, 0, GRID);
    for (Node* leaf : leaf_nodes) {
        int id = leaf->company_id;
        rects[id][0] = leaf->lx;
        rects[id][1] = leaf->ly;
        rects[id][2] = leaf->rx;
        rects[id][3] = leaf->ry;
    }

    // Local optimization
    double current_score = compute_score();
    const double eps = 1e-9;
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    bool improved = true;
    int iter = 0;
    while (improved && iter < 1000) {
        improved = false;
        shuffle(internal_nodes.begin(), internal_nodes.end(), rng);
        for (Node* node : internal_nodes) {
            int old_split = node->split;
            // Try +1
            if (node->split + 1 <= node->high_bound) {
                node->split = old_split + 1;
                update_rectangles(root, 0, GRID, 0, GRID);
                double new_score = compute_score();
                if (new_score > current_score + eps) {
                    current_score = new_score;
                    improved = true;
                    continue;
                } else {
                    node->split = old_split;
                }
            }
            // Try -1
            if (node->split - 1 >= node->low_bound) {
                node->split = old_split - 1;
                update_rectangles(root, 0, GRID, 0, GRID);
                double new_score = compute_score();
                if (new_score > current_score + eps) {
                    current_score = new_score;
                    improved = true;
                    continue;
                } else {
                    node->split = old_split;
                }
            }
        }
        ++iter;
    }

    // Final update
    update_rectangles(root, 0, GRID, 0, GRID);
    for (Node* leaf : leaf_nodes) {
        int id = leaf->company_id;
        rects[id][0] = leaf->lx;
        rects[id][1] = leaf->ly;
        rects[id][2] = leaf->rx;
        rects[id][3] = leaf->ry;
    }

    // Output
    for (int i = 0; i < n; ++i) {
        cout << rects[i][0] << " " << rects[i][1] << " " << rects[i][2] << " " << rects[i][3] << "\n";
    }

    return 0;
}