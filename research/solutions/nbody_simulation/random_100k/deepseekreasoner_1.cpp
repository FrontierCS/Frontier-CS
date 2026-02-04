#include <vector>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <immintrin.h>
#include <omp.h>

struct BoundingBox {
    float min_x, max_x, min_y, max_y;
    
    BoundingBox() : min_x(1e9), max_x(-1e9), min_y(1e9), max_y(-1e9) {}
    
    void update(float x, float y) {
        min_x = std::min(min_x, x);
        max_x = std::max(max_x, x);
        min_y = std::min(min_y, y);
        max_y = std::max(max_y, y);
    }
    
    void expand(float margin) {
        min_x -= margin;
        max_x += margin;
        min_y -= margin;
        max_y += margin;
    }
};

struct QuadNode {
    float center_x, center_y, half_width;
    int start_idx, end_idx;
    int children[4];
    float total_mass;
    float com_x, com_y;
    bool is_leaf;
    
    QuadNode() : start_idx(0), end_idx(0), total_mass(0), 
                 com_x(0), com_y(0), is_leaf(true) {
        children[0] = children[1] = children[2] = children[3] = -1;
    }
};

class MySimulator : public Simulator {
private:
    int numThreads = 16;
    std::vector<QuadNode> quad_nodes;
    std::vector<int> particle_indices;
    std::vector<Vec2> accumulated_forces;
    std::vector<float> cell_centers_x;
    std::vector<float> cell_centers_y;
    std::vector<float> cell_masses;
    int grid_size;
    float grid_cell_size;
    float grid_inv_cell_size;
    float domain_min_x, domain_min_y;
    float domain_size;
    BoundingBox current_bbox;
    
    static constexpr float THETA = 0.5f; // Barnes-Hut opening criterion
    static constexpr float G = 0.01f;
    
    inline int get_grid_cell(float x, float y) const {
        int cx = static_cast<int>((x - domain_min_x) * grid_inv_cell_size);
        int cy = static_cast<int>((y - domain_min_y) * grid_inv_cell_size);
        cx = std::max(0, std::min(cx, grid_size - 1));
        cy = std::max(0, std::min(cy, grid_size - 1));
        return cy * grid_size + cx;
    }
    
    void build_quadtree(std::vector<Particle>& particles, 
                       std::vector<int>& indices, int start, int end,
                       float center_x, float center_y, float half_width, int node_idx) {
        if (end - start <= 32) { // Leaf node threshold
            quad_nodes[node_idx].start_idx = start;
            quad_nodes[node_idx].end_idx = end;
            quad_nodes[node_idx].is_leaf = true;
            
            // Compute center of mass for leaf
            float total_mass = 0;
            float com_x = 0, com_y = 0;
            for (int i = start; i < end; ++i) {
                int pidx = indices[i];
                float mass = particles[pidx].mass;
                total_mass += mass;
                com_x += mass * particles[pidx].position.x;
                com_y += mass * particles[pidx].position.y;
            }
            
            if (total_mass > 0) {
                quad_nodes[node_idx].total_mass = total_mass;
                quad_nodes[node_idx].com_x = com_x / total_mass;
                quad_nodes[node_idx].com_y = com_y / total_mass;
            }
            return;
        }
        
        // Count particles in each quadrant
        int counts[4] = {0, 0, 0, 0};
        float child_half = half_width * 0.5f;
        float child_centers_x[4], child_centers_y[4];
        
        child_centers_x[0] = center_x - child_half;
        child_centers_x[1] = center_x + child_half;
        child_centers_x[2] = center_x - child_half;
        child_centers_x[3] = center_x + child_half;
        
        child_centers_y[0] = center_y - child_half;
        child_centers_y[1] = center_y - child_half;
        child_centers_y[2] = center_y + child_half;
        child_centers_y[3] = center_y + child_half;
        
        std::vector<int> child_starts(4, start);
        for (int i = start; i < end; ++i) {
            int pidx = indices[i];
            float px = particles[pidx].position.x;
            float py = particles[pidx].position.y;
            
            int quadrant = 0;
            if (px > center_x) quadrant |= 1;
            if (py > center_y) quadrant |= 2;
            counts[quadrant]++;
        }
        
        for (int i = 1; i < 4; ++i) {
            child_starts[i] = child_starts[i-1] + counts[i-1];
        }
        
        std::vector<int> temp_indices(end - start);
        std::copy(indices.begin() + start, indices.begin() + end, temp_indices.begin());
        
        std::vector<int> child_pos(4);
        for (int i = 0; i < 4; ++i) child_pos[i] = child_starts[i];
        
        for (int idx = 0; idx < end - start; ++idx) {
            int pidx = temp_indices[idx];
            float px = particles[pidx].position.x;
            float py = particles[pidx].position.y;
            
            int quadrant = 0;
            if (px > center_x) quadrant |= 1;
            if (py > center_y) quadrant |= 2;
            
            indices[child_pos[quadrant]++] = pidx;
        }
        
        // Create child nodes
        float total_mass = 0;
        float com_x = 0, com_y = 0;
        quad_nodes[node_idx].is_leaf = false;
        
        for (int i = 0; i < 4; ++i) {
            if (counts[i] > 0) {
                int child_idx = quad_nodes.size();
                quad_nodes[node_idx].children[i] = child_idx;
                quad_nodes.emplace_back();
                
                build_quadtree(particles, indices, 
                              child_starts[i], child_starts[i] + counts[i],
                              child_centers_x[i], child_centers_y[i],
                              child_half, child_idx);
                
                total_mass += quad_nodes[child_idx].total_mass;
                com_x += quad_nodes[child_idx].total_mass * quad_nodes[child_idx].com_x;
                com_y += quad_nodes[child_idx].total_mass * quad_nodes[child_idx].com_y;
            }
        }
        
        if (total_mass > 0) {
            quad_nodes[node_idx].total_mass = total_mass;
            quad_nodes[node_idx].com_x = com_x / total_mass;
            quad_nodes[node_idx].com_y = com_y / total_mass;
        }
    }
    
    void compute_force_from_node(const Particle& pi, int node_idx, 
                                 float cullRadius, Vec2& force_acc) const {
        const QuadNode& node = quad_nodes[node_idx];
        
        if (node.total_mass == 0) return;
        
        float dx = node.com_x - pi.position.x;
        float dy = node.com_y - pi.position.y;
        float dist_sq = dx*dx + dy*dy;
        
        if (dist_sq < 1e-6f) return;
        
        float dist = std::sqrt(dist_sq);
        
        if (node.is_leaf || (node.half_width * 2.0f / dist < THETA)) {
            // Use center of mass approximation
            if (dist > cullRadius) return;
            
            float inv_dist = 1.0f / dist;
            dx *= inv_dist;
            
            if (dist < 0.1f) dist = 0.1f;
            float force_mag = pi.mass * node.total_mass * G / (dist * dist);
            
            if (dist > cullRadius * 0.75f) {
                float decay = 1.0f - (dist - cullRadius * 0.75f) / (cullRadius * 0.25f);
                force_mag *= decay;
            }
            
            force_acc.x += dx * force_mag;
            force_acc.y += dy * inv_dist * force_mag;
        } else {
            // Recurse into children
            for (int i = 0; i < 4; ++i) {
                if (node.children[i] != -1) {
                    compute_force_from_node(pi, node.children[i], cullRadius, force_acc);
                }
            }
        }
    }

public:
    void init(int numParticles, StepParameters params) override {
        omp_set_num_threads(numThreads);
        particle_indices.resize(numParticles);
        accumulated_forces.resize(numParticles);
        
        // Initialize particle indices
        #pragma omp parallel for
        for (int i = 0; i < numParticles; ++i) {
            particle_indices[i] = i;
        }
        
        // Set up spatial grid for broad phase
        grid_cell_size = params.cullRadius;
        grid_inv_cell_size = 1.0f / grid_cell_size;
        
        // Assume particles are within reasonable bounds
        domain_size = 100.0f; // Based on problem statement
        domain_min_x = 0.0f;
        domain_min_y = 0.0f;
        grid_size = static_cast<int>(domain_size / grid_cell_size) + 1;
        
        cell_centers_x.resize(grid_size * grid_size);
        cell_centers_y.resize(grid_size * grid_size);
        cell_masses.resize(grid_size * grid_size);
    }
    
    void simulateStep(std::vector<Particle> &particles,
                      std::vector<Particle> &newParticles,
                      StepParameters params) override {
        int N = particles.size();
        
        // Reset forces
        #pragma omp parallel for
        for (int i = 0; i < N; ++i) {
            accumulated_forces[i] = Vec2{0.0f, 0.0f};
        }
        
        // 1. Build quadtree
        quad_nodes.clear();
        quad_nodes.emplace_back();
        quad_nodes[0].center_x = 50.0f; // Center of domain
        quad_nodes[0].center_y = 50.0f;
        quad_nodes[0].half_width = 50.0f; // Half of domain size
        
        build_quadtree(particles, particle_indices, 0, N, 
                      50.0f, 50.0f, 50.0f, 0);
        
        // 2. Compute forces using quadtree with OpenMP
        #pragma omp parallel for schedule(dynamic, 64)
        for (int i = 0; i < N; ++i) {
            const Particle& pi = particles[i];
            Vec2 force{0.0f, 0.0f};
            
            // Compute force from quadtree
            compute_force_from_node(pi, 0, params.cullRadius, force);
            
            // Store accumulated force
            accumulated_forces[i] = force;
        }
        
        // 3. Update particles
        #pragma omp parallel for
        for (int i = 0; i < N; ++i) {
            newParticles[i] = updateParticle(particles[i], accumulated_forces[i], params.deltaTime);
        }
    }
};

Simulator* createSimulator() {
    return new MySimulator();
}