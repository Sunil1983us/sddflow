-- CreateEnum
CREATE TYPE "Priority" AS ENUM ('low', 'medium', 'high');

-- CreateEnum
CREATE TYPE "Status" AS ENUM ('open', 'in_progress', 'done');

-- CreateTable
CREATE TABLE "tasks" (
    "id" TEXT NOT NULL,
    "user_id" TEXT NOT NULL,
    "title" VARCHAR(200) NOT NULL,
    "description" VARCHAR(2000),
    "due_date" TIMESTAMP(3),
    "priority" "Priority" NOT NULL DEFAULT 'medium',
    "status" "Status" NOT NULL DEFAULT 'open',
    "completed_at" TIMESTAMP(3),
    "archived" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "tasks_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "idx_tasks_user_created" ON "tasks"("user_id", "created_at" DESC);

-- CreateIndex
CREATE INDEX "idx_tasks_user_status" ON "tasks"("user_id", "status");

-- CreateIndex
CREATE INDEX "idx_tasks_purge" ON "tasks"("status", "completed_at");
